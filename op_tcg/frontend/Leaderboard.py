import pandas as pd
import streamlit as st
from streamlit_elements import elements, dashboard, mui

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.matches import LeaderElo, BQLeaderElos
from op_tcg.frontend.sidebar import display_meta_sidebar, display_only_official_sidebar
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_data
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell, value2color_table_cell

st.set_page_config(layout="wide")

def display_leaderboard_table(df_leader_elos: pd.DataFrame, leader_id2leader_data: dict[str, Leader]):
    def lid2name(leader_id: str) -> str:
        return leader_id2leader_data.get(leader_id).name

    def lid2meta(leader_id: str) -> MetaFormat | str:
        return leader_id2leader_data.get(leader_id).id.split("-")[0]

    # data preprocessing
    display_columns = ["Release Set", "Name", "Elo"]
    #df_leader_elos["Meta"] = df_leader_elos["meta_format"].apply(lambda meta_format: meta_format)
    df_leader_elos["Release Set"] = df_leader_elos["leader_id"].apply(lambda lid: lid.split("-")[0])
    df_leader_elos["Name"] = df_leader_elos["leader_id"].apply(lambda lid: leader_id2leader_data[lid].name)
    df_leader_elos["Elo"] = df_leader_elos["elo"].apply(lambda elo: elo)

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("table_item", 0, 0, 6, 6, isResizable=False, isDraggable=False),
        ]

        with dashboard.Grid(layout):
            index_cells = [[create_image_cell(leader_id2leader_data[leader_id].image_aa_url,
                                              lid2meta(leader_id) + "\n" + lid2name(leader_id),
                                              overlay_color=leader_id2leader_data[leader_id].to_hex_color(),
                                              horizontal=True,
                                              show_text=False) for
                            i, leader_id in df_leader_elos["leader_id"].items()]]
            # keep only relevant columns
            df_leader_elos = df_leader_elos.drop(
                columns=[c for c in df_leader_elos.columns if c not in display_columns])
            header_cells = [mui.TableCell(children="Leader")] + [mui.TableCell(col) for col in
                                                                 df_leader_elos.columns.values]

            df_leader_elos_display = df_leader_elos.copy()
            for col in df_leader_elos_display.columns.values:
                #df_leader_elos_display = df_leader_elos_display.map(lambda x: mui.TableCell(str(x)))
                if col == "Elo":
                    max_elo = df_leader_elos_display[col].max()
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda elo: value2color_table_cell(elo, max=max_elo, color_switch_threshold=1000))
                else:
                    df_leader_elos_display[col] = df_leader_elos_display[col].apply(lambda x: mui.TableCell(str(x)))
            #df_leader_elos_display["Elo"] = df_leader_elos["Elo"].apply(lambda elo: win_rate2color_table_cell(60, cell_input=mui.Typography(elo)))

            display_table(df_leader_elos_display,
                          index_cells=index_cells,
                          header_cells=header_cells,
                          title=None,
                          key="table_item")


def main():
    # display data
    st.header("One Piece TCG Elo Leaderboard")
    meta_formats: list[MetaFormat] = display_meta_sidebar(multiselect=False)
    only_official: bool = display_only_official_sidebar()

    # get data
    leader_elos: list[LeaderElo] = get_leader_elo_data(meta_formats=meta_formats)
    sorted_leader_elo_data: list[LeaderElo] = sorted(leader_elos, key=lambda x: x.elo,
                                                     reverse=True)
    bq_leaders: list[Leader] = get_leader_data()
    leader_id2leader_data: dict[str, Leader] = {bq_leader_data.id: bq_leader_data for bq_leader_data in
                                                bq_leaders}

    if sorted_leader_elo_data:
        # display table.
        df_leader_elos = BQLeaderElos(elo_ratings=sorted_leader_elo_data).to_dataframe()
        # only selected meta data
        df_leader_elos = df_leader_elos[df_leader_elos["only_official"] == only_official]
        display_leaderboard_table(df_leader_elos, leader_id2leader_data)
    else:
        st.warning("Seems like the selected meta does not contain any matches")

if __name__ == "__main__":
    main()
