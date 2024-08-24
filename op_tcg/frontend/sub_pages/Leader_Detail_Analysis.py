import base64
import os
from functools import partial

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
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param, delete_query_param
from op_tcg.frontend.views.decklist import display_list_view


Q_PARAM_BEST_OPPONENT = "best_opponent_lid"
Q_PARAM_WORST_OPPONENT = "worst_opponent_lid"

class Matchup(BaseModel):
    id: str
    win_rate: float
    meta_format: MetaFormat
    total_matches: int

class OpponentMatchups(BaseModel):
    best_matchups: list[Matchup]
    worst_matchups: list[Matchup]

def get_img_with_href(img_url, target_url):
    html_code = f'''
        <a href="{target_url}">
            <img src="{img_url}" />
        </a>'''
    return html_code

def display_leader_dashboard(leader_data: LeaderExtended, leader_extended_data: list[LeaderExtended], radar_chart_data, decklist_data: DecklistData, decklist_card_ids: list[str], opponent_matchups: OpponentMatchups):
    # TODO simplify first 6 lines
    selected_best_opponent_id = lname_and_lid_to_lid(get_default_leader_name([m.id for m in opponent_matchups.best_matchups], query_param=Q_PARAM_BEST_OPPONENT))
    selected_worst_opponent_id = lname_and_lid_to_lid(get_default_leader_name([m.id for m in opponent_matchups.worst_matchups], query_param=Q_PARAM_WORST_OPPONENT))
    if selected_best_opponent_id == selected_worst_opponent_id:
        st.error("Selected best and worst opponent cannot be the same")
        return None
    opponent_matchups.worst_matchups = [m for m in opponent_matchups.worst_matchups if m.id != selected_best_opponent_id]
    opponent_matchups.best_matchups = [m for m in opponent_matchups.best_matchups if m.id != selected_worst_opponent_id]
    best_opponent_data: LeaderExtended | None = None
    worst_opponent_data: LeaderExtended | None = None
    with suppress(Exception):
        best_opponent_data = [le for le in leader_extended_data if le.id == selected_best_opponent_id][0]
    with suppress(Exception):
        worst_opponent_data = [le for le in leader_extended_data if le.id == selected_worst_opponent_id][0]


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
               create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.name],
                                               colors=[leader_data.to_hex_color()])

    tab1, tab2 = st.tabs(["Opponents", "Decklist"])
    with tab1:
        col1, col2, col3 = st.columns([0.3, 0.3, 0.3])
        with col1:
            display_opponent_view(best_opponent_data.id, opponent_matchups.best_matchups, leader_extended_data, best_matchup=True)
        with col2:
            with elements("nivo_chart_radar_with_opponent"):
                st.subheader("Win Rate Matchup")
                with mui.Box(sx={"height": 300}):
                    create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.name, worst_opponent_data.name,
                                                                          best_opponent_data.name],
                                                       colors=[leader_data.to_hex_color(),
                                                               worst_opponent_data.to_hex_color(),
                                                               best_opponent_data.to_hex_color()])
        with col3:
            display_opponent_view(worst_opponent_data.id, opponent_matchups.worst_matchups, leader_extended_data, best_matchup=False)
    with tab2:
        st.subheader("Decklist")
        col1, col2 = st.columns([0.4, 0.5])

        with col1:
            display_list_view(decklist_data, decklist_card_ids)


def display_opponent_view(selected_opponent_id: str, matchups: list[Matchup], leader_extended_data: list[LeaderExtended], best_matchup: bool):
    opponent_index = next(i for i, obj in enumerate(matchups) if obj.id == selected_opponent_id)
    opponent_matchup = matchups[opponent_index]
    opponent_leader_data = [le for le in leader_extended_data if le.id == opponent_matchup.id][0]
    opponent_leader_names = [lid_to_name_and_lid(m.id) for m in matchups]
    st.subheader(("Easiest" if best_matchup else "Hardest") + " Matchup")
    display_leader_select(available_leader_ids=opponent_leader_names,
                                                      key=f"select_opp_lid_{selected_opponent_id}",
                                                      multiselect=False,
                                                      default=opponent_leader_names[opponent_index],
                                                      on_change=add_query_param,
                                                      kwargs={Q_PARAM_BEST_OPPONENT if best_matchup else Q_PARAM_WORST_OPPONENT: f"select_opp_lid_{selected_opponent_id}"})
    img_with_href = get_img_with_href(opponent_leader_data.aa_image_url, f'/Leader_Detail_Analysis?lid={opponent_leader_data.id}')
    st.markdown(img_with_href, unsafe_allow_html=True)
    st.markdown(f"""  
\
\
    **Win Rate**: {int(round(opponent_matchup.win_rate, 2) * 100)}%  
    **Number Matches**: {opponent_matchup.total_matches}
    """)


def get_best_and_worst_opponent(df_meta_win_rate_data) -> OpponentMatchups:
    def create_matchup(df_row) -> Matchup:
        return Matchup(
            id=df_row["opponent_id"],
            win_rate=df_row["win_rate"],
            meta_format=df_row["meta_format"],
            total_matches=df_row["total_matches"],
        )

    max_total_matches = df_meta_win_rate_data["total_matches"].max()
    threshold = int(max_total_matches/10)
    df_sorted = df_meta_win_rate_data.query("total_matches > " + str(threshold)).sort_values("win_rate")
    worst_matchups = [create_matchup(df_row) for i, df_row in df_sorted.iterrows()]
    best_matchups = worst_matchups.copy()
    best_matchups.reverse()
    return OpponentMatchups(best_matchups=best_matchups,
                            worst_matchups=worst_matchups)


def main_leader_detail_analysis():
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    available_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data]))
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids, query_param="lid")
    only_official = True
    selected_meta_formats = [MetaFormat.latest_meta_format()]

    with st.sidebar:
        def on_change_fn(qparam2session_key: dict[str, str]):
            add_query_param(qparam2session_key)
            delete_query_param(Q_PARAM_BEST_OPPONENT)
            delete_query_param(Q_PARAM_WORST_OPPONENT)
        selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_names, key="select_lid",
                                                              multiselect=False, default=default_leader_name, on_change=partial(on_change_fn, qparam2session_key={"lid": "select_lid"}))
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

        leader_ids = list(set([leader_extended.id, *[matchup.id for matchup in opponent_matchups.worst_matchups], *[matchup.id for matchup in opponent_matchups.best_matchups]]))
        _, _, df_color_win_rates = get_win_rate_dataframes(
            df_meta_win_rate_data, leader_ids)
        radar_chart_data: list[dict[str, str | float]] = get_radar_chart_data(df_color_win_rates)

        display_leader_dashboard(leader_extended, leader_extended_data, radar_chart_data, decklist_data, card_ids_filtered, opponent_matchups)
    else:
        st.warning(f"No data available for Leader {leader_id}")

