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
from op_tcg.frontend.sidebar import display_leader_select, display_meta_select
from op_tcg.frontend.utils.chart import create_leader_line_chart, LineChartYValue, create_leader_win_rate_radar_chart, \
    get_radar_chart_data, create_line_chart
from op_tcg.frontend.utils.decklist import DecklistData, tournament_standings2decklist_data
from op_tcg.frontend.utils.extract import get_leader_extended, get_leader_win_rate, get_tournament_standing_data
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid, get_win_rate_dataframes
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param, delete_query_param
from op_tcg.frontend.utils.styles import read_style_sheet, css_rule_to_dict, PRIMARY_COLOR_RGB
from op_tcg.frontend.utils.utils import sort_df_by_meta_format
from op_tcg.frontend.views.decklist import display_list_view


Q_PARAM_EASIEST_OPPONENT = "easiest_opponent_lid"
Q_PARAM_HARDEST_OPPONENT = "hardest_opponent_lid"

class Matchup(BaseModel):
    leader_id: str
    win_rate: float
    total_matches: int
    meta_formats: list[MetaFormat]
    win_rate_chart_data: dict[MetaFormat, float]


class OpponentMatchups(BaseModel):
    easiest_matchups: list[Matchup]
    hardest_matchups: list[Matchup]

def get_img_with_href(img_url, target_url):
    html_code = f'''
        <a href="{target_url}" target="_self" >
            <img src="{img_url}" />
        </a>'''
    return html_code

def get_leader_data(matchups: list[Matchup], leader_extended_data: list[LeaderExtended], q_param: str) -> LeaderExtended | None:
    selected_opponent_id: str = lname_and_lid_to_lid(get_default_leader_name([m.leader_id for m in matchups], query_param=q_param))
    opponent_data: LeaderExtended | None = None
    with suppress(Exception):
        # if selected_opponent_id is None:
        #     opponent_data = leader_extended_data[0]
        # else:
        opponent_data = list(filter(lambda le: le.id == selected_opponent_id, leader_extended_data))[0]
    return opponent_data

def display_leader_dashboard(leader_data: LeaderExtended, leader_extended_data: list[LeaderExtended], radar_chart_data, decklist_data: DecklistData, decklist_card_ids: list[str], opponent_matchups: OpponentMatchups):
    easiest_opponent_data: LeaderExtended | None = get_leader_data(opponent_matchups.easiest_matchups, leader_extended_data, q_param=Q_PARAM_EASIEST_OPPONENT)
    hardest_opponent_data: LeaderExtended | None = get_leader_data(opponent_matchups.hardest_matchups, leader_extended_data, q_param=Q_PARAM_HARDEST_OPPONENT)
    # remove selected easiest opponent data from hardest matchups and vice versa
    opponent_matchups.easiest_matchups = [m for m in opponent_matchups.easiest_matchups if m.leader_id != hardest_opponent_data.id]
    opponent_matchups.hardest_matchups = [m for m in opponent_matchups.hardest_matchups if m.leader_id != easiest_opponent_data.id]
    if (easiest_opponent_data and hardest_opponent_data) and (easiest_opponent_data.id == hardest_opponent_data.id):
        st.error("Selected best and worst opponent cannot be the same")
        return None

    col1, col2, col3 = st.columns([0.25, 0.05, 0.5])
    col1.markdown("")
    col1.image(leader_data.aa_image_url)
    with col3:
        with elements("nivo_chart_line"):
            st.subheader("Win Rate Chart")
            rounder_corners_css = css_rule_to_dict(read_style_sheet("chart", selector=".rounded-corners"))
            with mui.Box(sx={"height": 150,
                             **rounder_corners_css,
                             "background": f"rgb{PRIMARY_COLOR_RGB}"
                             }):
                create_leader_line_chart(leader_id=leader_data.id, leader_extended=leader_extended_data,
                                                 enable_x_axis=True, enable_y_axis=False,
                                                 y_value=LineChartYValue.WIN_RATE)
        with elements("nivo_chart_radar"):
            st.subheader("Win Rate Matchup")
            with mui.Box(sx={"height": 250,
                             **rounder_corners_css,
                             "background": f"rgb{PRIMARY_COLOR_RGB}"
                             }):
               create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.name],
                                               colors=[leader_data.to_hex_color()])

    tab1, tab2 = st.tabs(["Opponents", "Decklist"])
    with tab1:
        col1, col2, col3 = st.columns([0.3, 0.3, 0.3])
        with col1:
            display_opponent_view(easiest_opponent_data.id, opponent_matchups.easiest_matchups, leader_extended_data, best_matchup=True)
        with col2:
            with elements("nivo_chart_radar_with_opponent"):
                st.subheader("Win Rate Matchup")
                with mui.Box(sx={"height": 300,
                                 **rounder_corners_css,
                                 "background": f"rgb{PRIMARY_COLOR_RGB}"}):
                    create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.name, hardest_opponent_data.name,
                                                                          easiest_opponent_data.name],
                                                       colors=[leader_data.to_hex_color(),
                                                               hardest_opponent_data.to_hex_color(),
                                                               easiest_opponent_data.to_hex_color()])
        with col3:
            display_opponent_view(hardest_opponent_data.id, opponent_matchups.hardest_matchups, leader_extended_data, best_matchup=False)
    with tab2:
        st.subheader("Decklist")
        col1, col2 = st.columns([0.4, 0.5])

        with col1:
            display_list_view(decklist_data, decklist_card_ids)


def display_opponent_view(selected_opponent_id: str, matchups: list[Matchup], leader_extended_data: list[LeaderExtended], best_matchup: bool):
    if not any(m.leader_id == selected_opponent_id for m in matchups):
        st.warning(f"Selected opponent {selected_opponent_id} has no matchup data")
        return None
    opponent_index = next(i for i, obj in enumerate(matchups) if obj.leader_id == selected_opponent_id)
    opponent_matchup = matchups[opponent_index]
    opponent_leader_data = [le for le in leader_extended_data if le.id == opponent_matchup.leader_id][0]
    opponent_leader_names = [lid_to_name_and_lid(m.leader_id) for m in matchups]
    st.subheader(("Easiest" if best_matchup else "Hardest") + " Matchup")
    display_leader_select(available_leader_ids=opponent_leader_names,
                          key=f"select_opp_lid_{selected_opponent_id}",
                          multiselect=False,
                          default=opponent_leader_names[opponent_index],
                          on_change=add_query_param,
                          kwargs={Q_PARAM_EASIEST_OPPONENT if best_matchup else Q_PARAM_HARDEST_OPPONENT: f"select_opp_lid_{selected_opponent_id}"})
    img_with_href = get_img_with_href(opponent_leader_data.aa_image_url, f'/Leader_Detail_Analysis?lid={opponent_leader_data.id}')
    st.markdown(img_with_href, unsafe_allow_html=True)
    st.markdown(f"""  
\
\
    **Win Rate**: {int(round(opponent_matchup.win_rate, 2) * 100)}%  
    **Number Matches**: {opponent_matchup.total_matches}  
    **Meta Formats**: {','.join(opponent_matchup.meta_formats)}
    """)

    with elements(f"nivo_chart_line_opponent_{best_matchup}"):
        st.subheader("Win Rate Change")
        with mui.Box(sx={"height": 150}):
            create_line_chart(opponent_matchup.win_rate_chart_data, data_id="WR", enable_x_axis=True, enable_y_axis=False)


def get_best_and_worst_opponent(df_meta_win_rate_data, meta_formats: list[MetaFormat], exclude_leader_ids: list[str] | None = None) -> OpponentMatchups:
    def create_matchup(df_group, win_rate_chart_data) -> Matchup:
        return Matchup(
            leader_id=df_group.iloc[0]["opponent_id"],
            win_rate=df_group["win_rate"].mean(),
            meta_formats=df_group["meta_format"].to_list(),
            total_matches=df_group["total_matches"].sum(),
            win_rate_chart_data={meta: round(wr,2) for meta, wr in win_rate_chart_data.items()},
        )
    exclude_leader_ids = exclude_leader_ids or []

    # sort dataframe
    df_meta_win_rate_data = sort_df_by_meta_format(df_meta_win_rate_data)
    leader_id2win_rate_chart_data: dict[str, dict[MetaFormat, float]] = df_meta_win_rate_data.groupby("opponent_id").apply(lambda df_group: df_group[["meta_format", "win_rate"]].set_index("meta_format")["win_rate"].to_dict()).to_dict()
    # drop data not in selected meta format
    df_meta_win_rate_data = df_meta_win_rate_data.query("meta_format in @meta_formats")

    max_total_matches = df_meta_win_rate_data["total_matches"].max()
    # min 10 or 10% of the max total matches
    threshold = min(int(max_total_matches/10), 10)
    df_sorted = df_meta_win_rate_data.query(f"total_matches > {threshold}").sort_values("win_rate")

    matchups: list[Matchup] = df_sorted.query("opponent_id not in @exclude_leader_ids").groupby("opponent_id").apply(lambda df_group: create_matchup(df_group, leader_id2win_rate_chart_data[df_group.iloc[0]["opponent_id"]])).to_list()
    matchups.sort(key= lambda m: m.win_rate)
    worst_matchups = matchups.copy()
    matchups.sort(key= lambda m: m.win_rate, reverse=True)
    best_matchups = matchups.copy()
    return OpponentMatchups(easiest_matchups=best_matchups,
                            hardest_matchups=worst_matchups)


def main_leader_detail_analysis():
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    available_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data]))
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids, query_param="lid")
    only_official = True

    with st.sidebar:
        def on_change_fn(qparam2session_key: dict[str, str]):
            add_query_param(qparam2session_key)
            delete_query_param(Q_PARAM_EASIEST_OPPONENT)
            delete_query_param(Q_PARAM_HARDEST_OPPONENT)
        selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_names, key="select_lid",
                                                              multiselect=False, default=default_leader_name, on_change=partial(on_change_fn, qparam2session_key={"lid": "select_lid"}))
        selected_meta_formats: list[MetaFormat] = display_meta_select(multiselect=True)

    leader_extended = None
    if selected_leader_name:
        leader_id: str = lname_and_lid_to_lid(selected_leader_name)
        leader_extended_filtered = [le for le in leader_extended_data if le.meta_format in selected_meta_formats and le.id == leader_id and le.only_official == only_official]
        if len(leader_extended_filtered) > 0:
            leader_extended = leader_extended_filtered[0]


    st.header(f"Leader: {selected_leader_name}")
    if leader_extended:
        selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=MetaFormat.to_list())
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
        opponent_matchups = get_best_and_worst_opponent(df_meta_win_rate_data.query(f"leader_id == '{leader_extended.id}'"), meta_formats=selected_meta_formats, exclude_leader_ids=[leader_extended.id])

        leader_ids = list(set([leader_extended.id, *[matchup.leader_id for matchup in opponent_matchups.hardest_matchups], *[matchup.leader_id for matchup in opponent_matchups.easiest_matchups]]))
        _, _, df_color_win_rates = get_win_rate_dataframes(
            df_meta_win_rate_data.query("meta_format in @selected_meta_formats"), leader_ids)
        radar_chart_data: list[dict[str, str | float]] = get_radar_chart_data(df_color_win_rates)

        display_leader_dashboard(leader_extended, leader_extended_data, radar_chart_data, decklist_data, card_ids_filtered, opponent_matchups)
    else:
        st.warning(f"No data available for Leader {leader_id}")

