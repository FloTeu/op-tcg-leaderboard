import pandas as pd
import streamlit as st
from streamlit_elements import elements, dashboard, mui

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.matches import LeaderElo, BQLeaderElos
from op_tcg.frontend.sidebar import display_meta_sidebar, display_only_official_sidebar
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_data
from op_tcg.frontend.utils.material_ui_fns import display_table


def display_leaderboard_table(df_leader_elos: pd.DataFrame, leader_id2leader_data: dict[str, Leader]):
    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("table_item", 0, 3, 6, 6, isResizable=False, isDraggable=False),
        ]

        df_leader_elos = df_leader_elos.applymap(lambda x: mui.TableCell()(str(x)))
        with dashboard.Grid(layout):
            display_table(df_leader_elos,
                          index_cells=None,
                          header_cells=None,
                          title=None,
                          key="table_item")


def main():

    # display data
    st.header("One Piece TCG Elo Leaderboard")
    meta_formats: list[MetaFormat] = display_meta_sidebar()
    only_official: bool = display_only_official_sidebar()

    # get data
    leader_elos: list[LeaderElo] = get_leader_elo_data(meta_formats=meta_formats)
    sorted_leader_elo_data: list[LeaderElo] = sorted(leader_elos, key=lambda x: x.elo,
                                                     reverse=True)
    bq_leaders: list[Leader] = get_leader_data()
    leader_id2leader_data: dict[str, Leader] = {bq_leader_data.id: bq_leader_data for bq_leader_data in
                                                bq_leaders}

    # display table.
    df_leader_elos = BQLeaderElos(elo_ratings=sorted_leader_elo_data).to_dataframe()
    # only selected meta data
    df_leader_elos = df_leader_elos[df_leader_elos["only_official"] == only_official]
    display_leaderboard_table(df_leader_elos, leader_id2leader_data)


if __name__ == "__main__":
    main()