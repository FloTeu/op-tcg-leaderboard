import os

import pandas as pd
import streamlit as st

from op_tcg.frontend.sub_pages.constants import SUB_PAGE_LEADER_MATCHUP, SUB_PAGE_LEADER_DECKLIST, \
    SUB_PAGE_LEADER_DECKLIST_MOVEMENT, SUB_PAGE_CARD_POPULARITY

st.set_page_config(layout="wide")

from datetime import datetime, date
from uuid import uuid4

from op_tcg.backend.utils.utils import booleanize
from op_tcg.frontend.utils.launch import init_load_data
from op_tcg.backend.etl.load import bq_insert_rows, get_or_create_table
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import TournamentWinner, LeaderElo, LeaderExtended, Leader
from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.matches import Match, MatchResult, LeaderWinRate
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.frontend.utils.session import get_session_id
from op_tcg.frontend.sidebar import display_meta_select, display_only_official_toggle, display_release_meta_select, \
    display_match_count_slider_slider, display_leader_color_multiselect, display_leader_select, LeaderboardSortBy, \
    display_sortby_select
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_match_data, \
    get_leader_tournament_wins, get_leader_win_rate, get_leader_extended
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell, value2color_table_cell
from op_tcg.frontend.utils.leader_data import leader_id2aa_image_url, lid2ldata_fn, get_lid2ldata_dict_cached, \
    get_template_leader, lids_to_name_and_lids, lname_and_lid_to_lid
from op_tcg.frontend.utils.utils import bq_client
from op_tcg.frontend.sub_pages import main_meta_analysis, main_leader_detail_analysis_decklists, \
    main_leader_detail_anylsis, main_admin_leader_upload, main_leader_decklist_movement, main_card_meta_analysis

from streamlit_elements import elements, dashboard, mui, nivo
from streamlit_theme import st_theme

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}

from timer import timer


def leader_id2line_chart(leader_id: str, df_leader_extended, y_value: str = "elo"):
    # Streamlit Elements includes 45 dataviz components powered by Nivo.
    data_lines = df_leader_extended.query(f"id == '{leader_id}'").sort_values("meta_format")[
        ["meta_format", y_value]].rename(columns={"meta_format": "x", y_value: "y"}).to_dict(orient="records")
    colors = [
        "rgb(255, 107, 129)" if data_lines[-1]["y"] < data_lines[0]["y"] else "rgb(123, 237, 159)"
    ]
    for meta_format in sorted(MetaFormat.to_list(), reverse=True):
        # exclude OP01 since we have no official matches yet
        if meta_format not in data_lines and meta_format != MetaFormat.OP01:
            data_lines.insert(0, {"x": meta_format, "y": None})

    DATA = [
        {
            "id": "Elo" if y_value == "elo" else "WR",
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


def display_leaderboard_table(df_leader_extended: LeaderExtended.paSchema(), meta_format: MetaFormat, display_name2df_col_name: dict[str, str]):

    df_leader_extended['win_rate_decimal'] = df_leader_extended['win_rate'].apply(lambda x: f"{x * 100:.2f}%")
    # data preprocessing
    all_meta_formats = MetaFormat.to_list()
    relevant_meta_formats = all_meta_formats[:all_meta_formats.index(meta_format) + 1]
    df_leader_extended = df_leader_extended.query("meta_format in @relevant_meta_formats")
    df_leader_extended_selected_meta = df_leader_extended.query(f"meta_format == '{meta_format}'").copy()
    display_columns = ["Name", "Release Set", LeaderboardSortBy.TOURNAMENT_WINS, "Match Count",
                       LeaderboardSortBy.WIN_RATE, "Elo"]
    df_leader_extended_selected_meta["Release Set"] = df_leader_extended_selected_meta["id"].apply(
        lambda lid: lid.split("-")[0])
    # df_leader_extended_selected_meta["Name"] = df_leader_extended_selected_meta["id"]  # .apply(lambda lid: lid2ldata(lid).name.replace('"', " ").replace('.', " "))
    for display_name, df_col_name in display_name2df_col_name.items():
        if display_name == LeaderboardSortBy.WIN_RATE:
            df_col_name = "win_rate_decimal"
        df_leader_extended_selected_meta[str(display_name)] = df_leader_extended_selected_meta[df_col_name]


    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("lboard_table_item", 0, 0, 12, 6, isResizable=False, isDraggable=False),
        ]

        with dashboard.Grid(layout):
            index_cells = [[create_image_cell(df_row.aa_image_url,
                                              text=f"#{i + 1}",
                                              overlay_color=df_row.color_hex_code,
                                              horizontal=True) for
                            i, df_row in df_leader_extended_selected_meta.iterrows()]]
            # keep only relevant columns
            df_leader_elos_filtered = df_leader_extended_selected_meta.drop(
                columns=[c for c in df_leader_extended_selected_meta.columns if c not in (display_columns + ["id"])])[
                display_columns + ["id"]]
            header_cells = [mui.TableCell(children="Leader", sx={"width": "200px"})] + [mui.TableCell(col) for col in
                                                                                        (display_columns + [
                                                                                            "Win Rate Chart"])]

            df_leader_elos_display = df_leader_elos_filtered.copy()
            for col in display_columns:
                # df_leader_elos_display = df_leader_elos_display.map(lambda x: mui.TableCell(str(x)))
                if col == "Elo":
                    max_elo = df_leader_elos_display[col].max()
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(
                        lambda elo: value2color_table_cell(elo, max=max_elo,
                                                           color_switch_threshold=1000 if 1000 < max_elo else (
                                                                   max_elo * (7 / 8))))
                elif col == "Name":
                    df_leader_elos_display[col] = df_leader_elos_display[[col, "id"]].apply(lambda x: mui.TableCell(mui.Link(
                        str(x.Name.replace('"', " ").replace('.', " ")),
                        href=f"/{SUB_PAGE_LEADER_DECKLIST}?lid={x.id}", target="_blank")), axis=1)
                else:
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda x: mui.TableCell(str(x)))

            df_leader_elos_display = df_leader_elos_display.drop(columns=["id"])
            df_leader_elos_display["Elo Chart"] = df_leader_extended_selected_meta["id"].apply(
                lambda lid: leader_id2line_chart(lid, df_leader_extended, y_value="win_rate_decimal"))

            display_table(df_leader_elos_display,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title=None,
                          key="lboard_table_item")


def sort_table_df(df: LeaderExtended.paSchema(), sort_by: LeaderboardSortBy, display_name2df_col_name: dict[str, str]) -> LeaderExtended.paSchema():
    df_col_name = display_name2df_col_name[sort_by]
    # sort table
    if sort_by == LeaderboardSortBy.TOURNAMENT_WINS:
        # Custom sorting key
        df['sort_key'] = df.apply(lambda row: (row[df_col_name] > 0, row[df_col_name], row[display_name2df_col_name[LeaderboardSortBy.ELO]]), axis=1)
        # Sort the DataFrame using the custom sort key
        df = df.sort_values(by='sort_key', ascending=False).reset_index()
        # Drop the temporary sort key column
        df = df.drop(columns=['sort_key'])
    else:
        df = df.sort_values(df_col_name, ascending=False).reset_index()
    return df


@st.experimental_dialog("Upload Match")
def upload_match_dialog():
    leader_id2leader_data = get_lid2ldata_dict_cached()
    meta_format = display_meta_select(multiselect=False, key="upload_form_meta_format")[0]
    allowed_meta_fomats = MetaFormat.to_list()[0:MetaFormat.to_list().index(meta_format) + 1]
    with st.form("upload_match_form"):
        # TODO: Ensure right release meta is correctly included for each leader in db
        available_leader_ids = [lid for lid, ldata in leader_id2leader_data.items() if
                                ldata.release_meta in allowed_meta_fomats]
        available_leader_ids = sorted(available_leader_ids)
        # add name to ids (drop duplicates and ensures right order)
        available_leader_names: list[str] = lids_to_name_and_lids(
            list([lid for lid in dict.fromkeys(available_leader_ids) if lid in leader_id2leader_data]))

        # display user input
        today_date = datetime.now().date()
        match_day: date = st.date_input("Match Day", value=today_date, max_value=today_date)
        match_datetime: datetime = datetime.combine(match_day, datetime.now().time())

        selected_winner_leader_name: str | None = display_leader_select(available_leader_ids=available_leader_names,
                                                                        multiselect=False, label="Winner Leader",
                                                                        key="match_leader_id")
        selected_winner_leader_id: str | None = lname_and_lid_to_lid(
            selected_winner_leader_name) if selected_winner_leader_name is not None else None
        selected_loser_leader_name: str | None = display_leader_select(available_leader_ids=available_leader_names,
                                                                       multiselect=False, label="Looser Leader",
                                                                       key="match_opponentleader_id")
        selected_loser_leader_id: str | None = lname_and_lid_to_lid(
            selected_loser_leader_name) if selected_loser_leader_name is not None else None
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

    with st.spinner("Launch App"):
        init_load_data()

    with st.sidebar:
        meta_format: MetaFormat = display_meta_select(multiselect=False)[0]
        release_meta_formats: list[MetaFormat] | None = display_release_meta_select(multiselect=True)
        selected_leader_colors: list[OPTcgColor] | None = display_leader_color_multiselect()
        display_max_match_count = 10000
        match_count_min, match_count_max = display_match_count_slider_slider(min=0, max=display_max_match_count)
        only_official: bool = display_only_official_toggle()
        sort_by: LeaderboardSortBy = display_sortby_select()

    display_name2df_col_name = {
        "Name": "name",
        LeaderboardSortBy.TOURNAMENT_WINS.value: "tournament_wins",
        "Match Count": "total_matches",
        LeaderboardSortBy.WIN_RATE.value: "win_rate",
        LeaderboardSortBy.ELO.value: "elo",
    }
    # get data
    leader_extended_data: list[LeaderExtended] = get_leader_extended()

    # drop None values
    required_values = ["elo", "win_rate", "total_matches", "only_official"]
    leader_extended_data: list[LeaderExtended] = list(
        filter(lambda x: all(getattr(x, v) is not None for v in required_values), leader_extended_data))

    def filter_fn(le: LeaderExtended) -> bool:
        keep_le = le.only_official == only_official
        # filter release_meta_formats
        if release_meta_formats:
            keep_le = keep_le and (le.release_meta_format in release_meta_formats)
        # filter colors
        if selected_leader_colors:
            keep_le = keep_le and any(lcolor in selected_leader_colors for lcolor in le.colors)
        # filter match_count
        if match_count_min:
            keep_le = keep_le and (le.total_matches >= match_count_min)
        if match_count_max != display_max_match_count:
            keep_le = keep_le and (le.total_matches <= match_count_max)
        return keep_le

    # run filters
    leader_extended_data = list(filter(lambda x: filter_fn(x), leader_extended_data))

    if st.button("Upload Match"):
        upload_match_dialog()
    if leader_extended_data:
        # display table.
        df_leader_extended = pd.DataFrame([{**r.dict(), "color_hex_code": r.to_hex_color()} for r in leader_extended_data])
        df_leader_extended = sort_table_df(df_leader_extended, sort_by=sort_by, display_name2df_col_name=display_name2df_col_name)
        display_leaderboard_table(df_leader_extended, meta_format, display_name2df_col_name)
    else:
        st.warning("Seems like the selected meta does not contain any matches")


# main_meta_analysis, main_leader_detail_analysis_decklists, main_leader_detail_anylsis, main_admin_leader_upload
pages = [
    st.Page(main, title="Leaderboard", default=True),
    st.Page(main_meta_analysis, title=SUB_PAGE_LEADER_MATCHUP, url_path=SUB_PAGE_LEADER_MATCHUP),
    st.Page(main_leader_detail_analysis_decklists, title=SUB_PAGE_LEADER_DECKLIST, url_path=SUB_PAGE_LEADER_DECKLIST),
    st.Page(main_leader_decklist_movement, title=SUB_PAGE_LEADER_DECKLIST_MOVEMENT,
            url_path=SUB_PAGE_LEADER_DECKLIST_MOVEMENT),
    st.Page(main_card_meta_analysis, title=SUB_PAGE_CARD_POPULARITY, url_path=SUB_PAGE_CARD_POPULARITY),
]

# admin_password = st.sidebar.text_input("Show Admin Page")
# if admin_password in st.secrets["admin"]["emails"]:
#     pages.append(st.Page(main_admin_leader_upload, title='Admin_Leader_Upload', url_path="Admin_Leader_Upload"))

if booleanize(os.environ.get("DEBUG", "")):
    pages.append(st.Page(main_leader_detail_anylsis, title='Leader_Detail_Analysis', url_path="Leader_Detail_Analysis"))
    # if not admin_password in st.secrets["admin"]["emails"]:
    pages.append(st.Page(main_admin_leader_upload, title='Admin_Leader_Upload', url_path="Admin_Leader_Upload"))

pg = st.navigation(pages)
pg.run()
