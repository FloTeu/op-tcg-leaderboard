import pandas as pd
import streamlit as st

from datetime import datetime, date
from uuid import uuid4

from op_tcg.frontend.utils.launch import init_load_data
from op_tcg.backend.etl.load import bq_insert_rows, get_or_create_table
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import OPTcgColor, TournamentWinner, LeaderElo
from op_tcg.backend.models.matches import Match, MatchResult, LeaderWinRate
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.frontend.utils.session import get_session_id
from op_tcg.frontend.sidebar import display_meta_select, display_only_official_toggle, display_release_meta_select, \
    display_match_count_slider_slider, display_leader_color_multiselect, display_leader_select, LeaderboardSortBy, \
    display_sortby_select
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_match_data, \
    get_leader_tournament_wins, get_leader_win_rate
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell, value2color_table_cell
from op_tcg.frontend.utils.leader_data import leader_id2aa_image_url, lid2ldata, get_lid2ldata_dict_cached
from op_tcg.frontend.utils.utils import bq_client

from streamlit_elements import elements, dashboard, mui, nivo
from streamlit_theme import st_theme

st.set_page_config(layout="wide")
ST_THEME = st_theme() or {"base": "dark"}

from timer import timer

with st.spinner("Launch App"):
    init_load_data()

def leader_id2elo_chart(leader_id: str, df_leader_elos):
    # Streamlit Elements includes 45 dataviz components powered by Nivo.
    data_lines = df_leader_elos.query(f"leader_id == '{leader_id}'").sort_values("meta_format")[["meta_format", "elo"]].rename(columns={"meta_format": "x", "elo": "y"}).to_dict(orient="records")
    colors = [
        "rgb(255, 107, 129)" if data_lines[-1]["y"] < data_lines[0]["y"] else "rgb(123, 237, 159)"
    ]
    for meta_format in sorted(MetaFormat.to_list(), reverse=True):
        # exclude OP01 since we have no official matches yet
        if meta_format not in data_lines and meta_format != MetaFormat.OP01:
            data_lines.insert(0, {"x": meta_format, "y": None})

    DATA = [
      {
        "id": "Elo",
        "data": data_lines
      }
    ]

    radar_plot = nivo.Line(
        data=DATA,
        margin={"top": 10, "right": 20, "bottom": 10, "left": 10},
        enableGridX=False,
        enableGridY=False,
        yScale={
            "type": "linear",
            "min": "auto"
        },
        pointSize=10,
        pointBorderWidth=0,
        axisBottom=None,
        axisLeft=None,
        enableSlices="x",
        motionConfig="slow",
        colors=colors,
        theme={
            "background": "#2C3A47" if ST_THEME["base"] == "dark" else "#ffffff",
            "textColor": "#ffffff" if ST_THEME["base"] == "dark" else "#31333F",
            "tooltip": {
                "container": {
                    "background": "#FFFFFF",
                    "color": "#31333F",
                }
            }
        }
    )


    return mui.TableCell(mui.Box(radar_plot, sx={"height": 120, "width": 190}), sx={"padding": "0px"})


def display_leaderboard_table(meta_format: MetaFormat, df_all_leader_elos: pd.DataFrame, df_meta_win_rate_data: LeaderWinRate.paSchema(), df_tournament_wins: TournamentWinner.paSchema(), match_count_min: int=None, match_count_max: int=None, sort_by: LeaderboardSortBy = "elo"):
    def lid2match_count(leader_id: str) -> int:
        return df_meta_win_rate_data.query(f"leader_id == '{leader_id}'")["total_matches"].sum()
    def lid2win_rate(leader_id: str) -> str:
        df = df_meta_win_rate_data.query(f"leader_id == '{leader_id}'")
        weighted_average = (df['win_rate'] * df['total_matches']).sum() / df['total_matches'].sum()
        return f'{int(float("%.2f" % weighted_average) * 100)}%'

    def lid2tournament_wins(leader_id: str) -> int:
        return df_tournament_wins.query(f"leader_id == '{leader_id}'")["win_count"].sum()

    # data preprocessing
    all_meta_formats = MetaFormat.to_list()
    relevant_meta_formats = all_meta_formats[:all_meta_formats.index(meta_format)+1]
    df_all_leader_elos = df_all_leader_elos.query("meta_format in @relevant_meta_formats")
    df_leader_elos = df_all_leader_elos.query(f"meta_format == '{meta_format}'").copy()
    display_columns = ["Name", "Release Set", LeaderboardSortBy.TOURNAMENT_WINS, "Match Count", LeaderboardSortBy.WIN_RATE, "Elo"]
    #df_leader_elos["Meta"] = df_leader_elos["meta_format"].apply(lambda meta_format: meta_format)
    df_leader_elos["Release Set"] = df_leader_elos["leader_id"].apply(lambda lid: lid.split("-")[0])
    df_leader_elos["Name"] = df_leader_elos["leader_id"]#.apply(lambda lid: lid2ldata(lid).name.replace('"', " ").replace('.', " "))
    df_leader_elos["Match Count"] = df_leader_elos["leader_id"].apply(lambda lid: lid2match_count(lid))
    df_leader_elos[LeaderboardSortBy.WIN_RATE] = df_leader_elos["leader_id"].apply(lambda lid: lid2win_rate(lid))
    df_leader_elos[LeaderboardSortBy.TOURNAMENT_WINS] = df_leader_elos["leader_id"].apply(lambda lid: lid2tournament_wins(lid))
    df_leader_elos["Elo"] = df_leader_elos["elo"].apply(lambda elo: elo)
    if match_count_min:
        df_leader_elos = df_leader_elos.loc[df_leader_elos["Match Count"] > match_count_min]
    if match_count_max:
        df_leader_elos = df_leader_elos.loc[df_leader_elos["Match Count"] < match_count_max]

    # sort table
    if sort_by == LeaderboardSortBy.TOURNAMENT_WINS:
        # Custom sorting key
        df_leader_elos['sort_key'] = df_leader_elos.apply(lambda row: (row[sort_by] > 0, row[sort_by], row[LeaderboardSortBy.ELO]), axis=1)
        # Sort the DataFrame using the custom sort key
        df_leader_elos = df_leader_elos.sort_values(by='sort_key', ascending=False).reset_index()
        # Drop the temporary sort key column
        df_leader_elos = df_leader_elos.drop(columns=['sort_key'])
    else:
        df_leader_elos = df_leader_elos.sort_values(sort_by, ascending=False).reset_index()

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("lboard_table_item", 0, 0, 12, 6, isResizable=False, isDraggable=False),
        ]

        with dashboard.Grid(layout):
            index_cells = [[create_image_cell(leader_id2aa_image_url(leader_id),
                                              text=f"#{i+1}",
                                              overlay_color=lid2ldata(leader_id).to_hex_color(),
                                              horizontal=True) for
                            i, leader_id in df_leader_elos["leader_id"].items()]]
            # keep only relevant columns
            df_leader_elos_filtered = df_leader_elos.drop(
                columns=[c for c in df_leader_elos.columns if c not in display_columns])[display_columns]
            header_cells = [mui.TableCell(children="Leader", sx={"width": "200px"})] + [mui.TableCell(col) for col in
                                                                                        (display_columns + ["Elo Chart"])]

            df_leader_elos_display = df_leader_elos_filtered.copy()
            for col in display_columns:
                #df_leader_elos_display = df_leader_elos_display.map(lambda x: mui.TableCell(str(x)))
                if col == "Elo":
                    max_elo = df_leader_elos_display[col].max()
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda elo: value2color_table_cell(elo, max=max_elo, color_switch_threshold=1000 if 1000 < max_elo else (max_elo*(7/8))))
                elif col == "Name":
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda x: mui.TableCell(mui.Link(str(lid2ldata(x).name.replace('"', " ").replace('.', " ")), href=f"/Leader_Detail_Analysis_Decklists?lid={x}", target="_blank")))
                else:
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda x: mui.TableCell(str(x)))
            df_leader_elos_display["Elo Chart"] = df_leader_elos["leader_id"].apply(
                lambda lid: leader_id2elo_chart(lid, df_all_leader_elos))

            display_table(df_leader_elos_display,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title=None,
                          key="lboard_table_item")


@st.experimental_dialog("Upload Match")
def upload_match_dialog():
    leader_id2leader_data = get_lid2ldata_dict_cached()
    meta_format = display_meta_select(multiselect=False, key="upload_form_meta_format")[0]
    allowed_meta_fomats = MetaFormat.to_list()[0:MetaFormat.to_list().index(meta_format)+1]
    with st.form("upload_match_form"):
        # TODO: Ensure right release meta is correctly included for each leader in db
        available_leader_ids = [lid for lid, ldata in leader_id2leader_data.items() if ldata.release_meta in allowed_meta_fomats]
        available_leader_ids = sorted(available_leader_ids)
        # add name to ids (drop duplicates and ensures right order)
        available_leader_names: list[str] = list(dict.fromkeys(
           [
               f"{leader_id2leader_data[lid].name if lid in leader_id2leader_data else ''} ({lid})"
               for lid
               in available_leader_ids]))
        # display user input
        today_date = datetime.now().date()
        match_day: date = st.date_input("Match Day", value=today_date, max_value=today_date)
        match_datetime: datetime = datetime.combine(match_day, datetime.now().time())

        selected_winner_leader_name: str | None = display_leader_select(available_leader_ids=available_leader_names, multiselect=False, label="Winner Leader", key="match_leader_id")
        selected_winner_leader_id: str | None = selected_winner_leader_name.split("(")[1].strip(")") if selected_winner_leader_name is not None else None
        selected_loser_leader_name: str | None = display_leader_select(available_leader_ids=available_leader_names, multiselect=False, label="Looser Leader", key="match_opponentleader_id")
        selected_loser_leader_id: str | None = selected_loser_leader_name.split("(")[1].strip(")") if selected_loser_leader_name is not None else None
        is_draw = st.checkbox("Is draw", value=False)

        # Every form must have a submit button.
        submitted = st.form_submit_button("Submit")
        if submitted:
            if selected_loser_leader_id is None or selected_winner_leader_id is None:
                st.warning("Winner or loser leader not yet selected")
            else:
                match_id = uuid4().hex
                session_id = get_session_id()
                rows_to_insert = []
                rows_to_insert.append(Match(id=match_id,
                    leader_id=selected_winner_leader_id,
                    opponent_id=selected_loser_leader_id,
                    result=MatchResult.DRAW if is_draw else MatchResult.WIN,
                    meta_format=meta_format,
                    official=False,
                    is_reverse=False,
                    source=session_id,
                    match_timestamp=match_datetime).model_dump()
                )
                rows_to_insert.append(Match(id=match_id,
                    leader_id=selected_loser_leader_id,
                    opponent_id=selected_winner_leader_id,
                    result=MatchResult.DRAW if is_draw else MatchResult.LOSE,
                    meta_format=meta_format,
                    official=False,
                    is_reverse=True,
                    source=session_id,
                    match_timestamp=match_datetime).model_dump()
                )

                bq_leader_table = get_or_create_table(model=Match, dataset_id=BQDataset.MATCHES,
                                                      client=bq_client)
                try:
                    bq_insert_rows(rows_to_insert, table=bq_leader_table, client=bq_client)
                    st.balloons()
                except Exception as e:
                    st.error(str(e))



def main():
    # display data
    st.header("One Piece TCG Elo Leaderboard")

    with st.sidebar:
        meta_formats: list[MetaFormat] = display_meta_select(multiselect=False)
        release_meta_formats: list[MetaFormat] | None = display_release_meta_select(multiselect=True)
        selected_leader_colors: list[OPTcgColor] | None = display_leader_color_multiselect()
        display_max_match_count=10000
        match_count_min, match_count_max = display_match_count_slider_slider(min=0, max=display_max_match_count)
        only_official: bool = display_only_official_toggle()
        sort_by: LeaderboardSortBy = display_sortby_select()

    # get data
    leader_elos: list[LeaderElo] = get_leader_elo_data()
    leader_tournament_wins: list[TournamentWinner] = get_leader_tournament_wins(meta_formats=meta_formats)

    # filter release_meta_formats
    if release_meta_formats:
        leader_elos: list[LeaderElo] = [lelo for lelo in leader_elos if lid2ldata(lelo.leader_id).release_meta in release_meta_formats]
    if selected_leader_colors:
        leader_elos: list[LeaderElo] = [lelo for lelo in leader_elos if any(lcolor in selected_leader_colors for lcolor in lid2ldata(lelo.leader_id).colors)]

    sorted_leader_elo_data: list[LeaderElo] = sorted(leader_elos, key=lambda x: x.elo,
                                                     reverse=True)

    selected_meta_leader_ids: list[str] = [lelo.leader_id for lelo in leader_elos]
    selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=meta_formats,
                                                                           leader_ids=selected_meta_leader_ids)
    df_meta_win_rate_data = pd.DataFrame([lwr.dict() for lwr in selected_meta_win_rate_data if (lwr.only_official if only_official else True)])
    df_tournament_wins = pd.DataFrame([twin.dict() for twin in leader_tournament_wins if twin.only_official == only_official])

    if st.button("Upload Match"):
        upload_match_dialog()
    if sorted_leader_elo_data:
        # display table.
        df_leader_elos = pd.DataFrame([r.dict() for r in sorted_leader_elo_data])
        # only selected meta data
        df_leader_elos = df_leader_elos[df_leader_elos["only_official"] == only_official]
        display_leaderboard_table(meta_formats[0], df_leader_elos, df_meta_win_rate_data, df_tournament_wins, match_count_min=match_count_min, match_count_max=match_count_max if match_count_max != display_max_match_count else None, sort_by=sort_by)
    else:
        st.warning("Seems like the selected meta does not contain any matches")

if __name__ == "__main__":
    main()
