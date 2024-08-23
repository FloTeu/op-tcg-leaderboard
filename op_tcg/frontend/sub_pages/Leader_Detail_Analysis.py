import pandas as pd
import streamlit as st
from contextlib import suppress
from pydantic import BaseModel
from streamlit_elements import elements, mui, dashboard, nivo, html as element_html

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.backend.models.tournaments import TournamentStandingExtended
from op_tcg.frontend.sidebar import display_leader_select
from op_tcg.frontend.utils.chart import create_leader_line_chart, LineChartYValue, create_leader_win_rate_radar_chart, \
    get_radar_chart_data
from op_tcg.frontend.utils.decklist import DecklistData, tournament_standings2decklist_data
from op_tcg.frontend.utils.extract import get_leader_extended, get_leader_win_rate, get_tournament_standing_data
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid, get_win_rate_dataframes
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param
from op_tcg.frontend.views.decklist import display_list_view


class Matchup(BaseModel):
    id: str
    win_rate: float
    meta_format: MetaFormat

class OpponentMatchups(BaseModel):
    best_matchup: Matchup
    worst_matchup: Matchup



def display_leader_dashboard(leader_data: LeaderExtended, leader_extended_data: list[LeaderExtended], radar_chart_data, decklist_data: DecklistData, decklist_card_ids: list[str], opponent_matchups: OpponentMatchups):
    best_opponent_data: LeaderExtended | None = None
    worst_opponent_data: LeaderExtended | None = None
    with suppress(Exception):
        best_opponent_data = [le for le in leader_extended_data if le.id == opponent_matchups.best_matchup.id][0]
    with suppress(Exception):
        worst_opponent_data = [le for le in leader_extended_data if le.id == opponent_matchups.worst_matchup.id][0]
    col1, col2, col3 = st.columns([0.25, 0.05, 0.5])
    col1.image(leader_data.aa_image_url)
    with col3:
        with elements("nivo_chart_line"):
            st.subheader("Win Rate Chart")
            with mui.Box(sx={"height": 150}):
                create_leader_line_chart(leader_id=leader_data.id, leader_extended=leader_extended_data,
                                                 enable_x_axis=True, enable_y_axis=False,
                                                 y_value=LineChartYValue.WIN_RATE)
        with elements("nivo_chart_radar"):
            st.subheader("Win Rate Matchup")
            with mui.Box(sx={"height": 250}):
               create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.name, worst_opponent_data.name, best_opponent_data.name],
                                               colors=[leader_data.to_hex_color(), worst_opponent_data.to_hex_color(), best_opponent_data.to_hex_color()])

    tab1, tab2 = st.tabs(["Opponents", "Decklist"])
    with tab1:
        col1, col2 = st.columns([0.4, 0.5])
        with col1:
            st.subheader("Best Matchup (%.2f)" % opponent_matchups.best_matchup.win_rate)
            st.image(best_opponent_data.aa_image_url)
            st.subheader("Worst Matchup (%.2f)" % opponent_matchups.worst_matchup.win_rate)
            st.image(worst_opponent_data.aa_image_url)
    with tab2:
        st.subheader("Decklist")
        col1, col2 = st.columns([0.4, 0.5])

        with col1:
            display_list_view(decklist_data, decklist_card_ids)

def get_best_and_worst_opponent(df_meta_win_rate_data) -> OpponentMatchups:
    def create_matchup(df_row) -> Matchup:
        return Matchup(
            id=df_row["opponent_id"],
            win_rate=df_row["win_rate"],
            meta_format=df_row["meta_format"]
        )

    max_total_matches = df_meta_win_rate_data["total_matches"].max()
    threshold = int(max_total_matches/10)
    df_sorted = df_meta_win_rate_data.query("total_matches > " + str(threshold)).sort_values("win_rate")
    return OpponentMatchups(best_matchup=create_matchup(df_sorted.iloc[-1]),
                            worst_matchup=create_matchup(df_sorted.iloc[0]))


def main_leader_detail_analysis():
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    available_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data]))
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids)
    only_official = True
    selected_meta_formats = [MetaFormat.latest_meta_format()]

    with st.sidebar:
        selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_names, key="select_lid",
                                                              multiselect=False, default=default_leader_name, on_change=add_query_param, kwargs={"lid": "select_lid"})
    leader_extended = None
    if selected_leader_name:
        leader_id: str = lname_and_lid_to_lid(selected_leader_name)
        meta_format = MetaFormat.latest_meta_format()
        leader_extended_filtered = [le for le in leader_extended_data if le.meta_format == meta_format and le.id == leader_id]
        if len(leader_extended_filtered) > 0:
            leader_extended = leader_extended_filtered[0]


    st.header(f"Leader: {selected_leader_name}")
    if leader_extended:
        selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=selected_meta_formats)
        df_meta_win_rate_data = pd.DataFrame(
            [lwr.dict() for lwr in selected_meta_win_rate_data if lwr.only_official == only_official])

        # Get decklist data
        tournament_standings: list[TournamentStandingExtended] = get_tournament_standing_data(
            meta_formats=selected_meta_formats, leader_id=leader_extended.id)
        decklist_data: DecklistData = tournament_standings2decklist_data(tournament_standings)
        card_ids_sorted = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                                 key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
        card_ids_filtered = [card_id for card_id in card_ids_sorted if
                             card_id != leader_extended.id and decklist_data.card_id2occurrence_proportion[card_id] >= 0.02]
        opponent_matchups = get_best_and_worst_opponent(df_meta_win_rate_data.query(f"leader_id == '{leader_extended.id}'"))

        _, _, df_color_win_rates = get_win_rate_dataframes(
            df_meta_win_rate_data, [leader_extended.id, opponent_matchups.worst_matchup.id, opponent_matchups.best_matchup.id])
        radar_chart_data: list[dict[str, str | float]] = get_radar_chart_data(df_color_win_rates)

        display_leader_dashboard(leader_extended, leader_extended_data, radar_chart_data, decklist_data, card_ids_filtered, opponent_matchups)
    else:
        st.warning(f"No data available for Leader {leader_id}")

