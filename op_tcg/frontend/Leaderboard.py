import pandas as pd
import streamlit as st

st.set_page_config(layout="wide")
from streamlit_elements import elements, dashboard, mui, nivo
from streamlit_theme import st_theme

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.matches import LeaderElo, BQLeaderElos, Match
from op_tcg.frontend.sidebar import display_meta_sidebar, display_only_official_sidebar, display_release_meta_sidebar
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_data, get_match_data
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell, value2color_table_cell
from op_tcg.frontend.utils.utils import leader_id2aa_image_url

ST_THEME = st_theme() or {"base": "dark"}

def leader_id2elo_chart(leader_id: str, df_leader_elos):
    # Streamlit Elements includes 45 dataviz components powered by Nivo.
    data_lines = df_leader_elos.query(f"leader_id == '{leader_id}'").sort_values("meta_format")[["meta_format", "elo"]].rename(columns={"meta_format": "x", "elo": "y"}).to_dict(orient="records")
    colors = [
        "rgb(255, 107, 129)" if data_lines[-1]["y"] < data_lines[0]["y"] else "rgb(123, 237, 159)"
    ]
    DATA = [
      {
        "id": "Elo",
        "data": data_lines
      }
    ]

    radar_plot = nivo.Line(
        data=DATA,
        margin={"top": 10, "right": 10, "bottom": 10, "left": 10},
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


    return mui.Box(radar_plot, sx={"height": 120, "width": 190})



def display_leaderboard_table(meta_format: MetaFormat, df_all_leader_elos: pd.DataFrame, df_meta_match_data, leader_id2leader_data: dict[str, Leader]):
    def lid2name(leader_id: str) -> str:
        return leader_id2leader_data.get(leader_id).name

    def lid2meta(leader_id: str) -> MetaFormat | str:
        return leader_id2leader_data.get(leader_id).id.split("-")[0]

    def lid2match_count(leader_id: str) -> int:
        return len(df_meta_match_data.query(f"leader_id == '{leader_id}'"))

    # data preprocessing
    all_meta_formats = MetaFormat.to_list()
    relevant_meta_formats = all_meta_formats[:all_meta_formats.index(meta_format)+1]
    df_all_leader_elos = df_all_leader_elos.query("meta_format in @relevant_meta_formats")
    df_leader_elos = df_all_leader_elos.query(f"meta_format == '{meta_format}'").sort_values("elo", ascending=False).reset_index()
    display_columns = ["Release Set", "Name", "Match Count", "Elo", "Elo Chart"]
    #df_leader_elos["Meta"] = df_leader_elos["meta_format"].apply(lambda meta_format: meta_format)
    df_leader_elos["Release Set"] = df_leader_elos["leader_id"].apply(lambda lid: lid.split("-")[0])
    df_leader_elos["Name"] = df_leader_elos["leader_id"].apply(lambda lid: leader_id2leader_data[lid].name.replace('"', " ").replace('.', " "))
    df_leader_elos["Match Count"] = df_leader_elos["leader_id"].apply(lambda lid: lid2match_count(lid))
    df_leader_elos["Elo"] = df_leader_elos["elo"].apply(lambda elo: elo)

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("lboard_table_item", 0, 0, 6, 6, isResizable=False, isDraggable=False),
        ]

        with dashboard.Grid(layout):
            index_cells = [[create_image_cell(leader_id2aa_image_url(leader_id,leader_id2leader_data),
                                              text=f"#{i+1}",
                                              overlay_color=leader_id2leader_data[leader_id].to_hex_color(),
                                              horizontal=True,
                                              sx={"width": "200px"}) for
                            i, leader_id in df_leader_elos["leader_id"].items()]]
            # keep only relevant columns
            df_leader_elos_filtered = df_leader_elos.drop(
                columns=[c for c in df_leader_elos.columns if c not in display_columns])
            header_cells = [mui.TableCell(children="Leader", sx={"width": "200px"})] + [mui.TableCell(col) for col in
                                                                 display_columns]

            df_leader_elos_display = df_leader_elos_filtered.copy()
            for col in display_columns:
                #df_leader_elos_display = df_leader_elos_display.map(lambda x: mui.TableCell(str(x)))
                if col == "Elo":
                    max_elo = df_leader_elos_display[col].max()
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda elo: value2color_table_cell(elo, max=max_elo, color_switch_threshold=1000))
                elif col == "Elo Chart":
                    df_leader_elos_display[col] = df_leader_elos["leader_id"].apply(lambda lid: leader_id2elo_chart(lid, df_all_leader_elos))
                else:
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda x: mui.TableCell(str(x)))
            #df_leader_elos_display["Elo"] = df_leader_elos["Elo"].apply(lambda elo: win_rate2color_table_cell(60, cell_input=mui.Typography(elo)))

            display_table(df_leader_elos_display,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title=None,
                          key="lboard_table_item")


def main():
    # display data
    st.header("One Piece TCG Elo Leaderboard")
    meta_formats: list[MetaFormat] = display_meta_sidebar(multiselect=False)
    release_meta_formats: list[MetaFormat] | None = display_release_meta_sidebar(multiselect=True)
    only_official: bool = display_only_official_sidebar()

    # get data
    leader_elos: list[LeaderElo] = get_leader_elo_data()

    bq_leaders: list[Leader] = get_leader_data()
    leader_id2leader_data: dict[str, Leader] = {bq_leader_data.id: bq_leader_data for bq_leader_data in
                                                bq_leaders}

    # filter release_meta_formats
    if release_meta_formats:
        leader_elos: list[LeaderElo] = [lelo for lelo in leader_elos if leader_id2leader_data[lelo.leader_id].release_meta in release_meta_formats]
    sorted_leader_elo_data: list[LeaderElo] = sorted(leader_elos, key=lambda x: x.elo,
                                                     reverse=True)

    selected_meta_leader_ids: list[str] = [lelo.leader_id for lelo in leader_elos]
    selected_meta_match_data: list[Match] = get_match_data(meta_formats=meta_formats,
                                                      leader_ids=selected_meta_leader_ids)
    df_meta_match_data = pd.DataFrame([match.dict() for match in selected_meta_match_data])
    if sorted_leader_elo_data:
        # display table.
        df_leader_elos = BQLeaderElos(elo_ratings=sorted_leader_elo_data).to_dataframe()
        # only selected meta data
        df_leader_elos = df_leader_elos[df_leader_elos["only_official"] == only_official]
        display_leaderboard_table(meta_formats[0], df_leader_elos, df_meta_match_data, leader_id2leader_data)
    else:
        st.warning("Seems like the selected meta does not contain any matches")

if __name__ == "__main__":
    main()
