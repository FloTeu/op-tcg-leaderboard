import pandas as pd
import streamlit as st
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

st.write("Example chart for leader performance vs different colors")

def display_leader_dashboard(leader_data: LeaderExtended, leader_extended_data: list[LeaderExtended], radar_chart_data):

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("leader_image", 0, 0, 2, 3, isDraggable=False, isResizable=False),
            dashboard.Item("leader_win_rate_line_chart", 3, 0, 4, 1, isDraggable=False, isResizable=False),
            dashboard.Item("lmeta_radar_plot_item_title", 3, 0, 4, 0.5, isDraggable=False, isResizable=False),
            dashboard.Item("leader_win_rate_radar_chart", 3, 0, 4, 2, isDraggable=False, isResizable=False),
        ]

        with dashboard.Grid(layout):
            #op_set = leader_data.id.split("-")[0]
            # mui.Box(component="img", src=image_url, alt=f"image_{card_id}", sx={"display": "flex"}, key=f"item_{card_id}")
            mui.Container(
                children=[
                    # Image at the top
                    element_html.Img(src=leader_data.aa_image_url, style={"width": "100%", "height": "auto"})
                ],
                key="leader_image"
            )
            mui.Box(key="leader_win_rate_line_chart",
                    children=[mui.Typography(
                            variant="h5",
                            component="h2",
                            children=f"Win Rate Chart",
                            gutterBottom=True
                        ),
                        create_leader_line_chart(leader_id=leader_data.id, leader_extended=leader_extended_data, enable_x_axis=True, enable_y_axis=False, y_value=LineChartYValue.WIN_RATE)
                    ],
                    sx={"border-radius": "10px;"})

            mui.Box(sx={"font-family": '"Source Sans Pro", sans-serif;', "margin-top": "50px"}, key="lmeta_radar_plot_item_title")(
                element_html.H2("Win Rate Matchup"))
            mui.Box(key="leader_win_rate_radar_chart", children=[
                create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.name], colors=[leader_data.to_hex_color()])
            ], sx={"margin-top": "10px"})

def main_leader_detail_analysis():
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    available_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data]))
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids)
    only_official =  True
    selected_meta_formats = [MetaFormat.latest_meta_format()]

    selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=selected_meta_formats)
    df_meta_win_rate_data = pd.DataFrame(
        [lwr.dict() for lwr in selected_meta_win_rate_data if lwr.only_official == only_official])

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
        # Get decklist data
        tournament_standings: list[TournamentStandingExtended] = get_tournament_standing_data(
            meta_formats=selected_meta_formats, leader_id=leader_extended.id)
        decklist_data: DecklistData = tournament_standings2decklist_data(tournament_standings)
        card_ids_sorted = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                                 key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
        card_ids_filtered = [card_id for card_id in card_ids_sorted if
                             card_id != leader_extended.id and decklist_data.card_id2occurrence_proportion[card_id] >= 0.02]

        _, _, df_color_win_rates = get_win_rate_dataframes(
            df_meta_win_rate_data, [leader_extended.id])
        radar_chart_data: list[dict[str, str | float]] = get_radar_chart_data(df_color_win_rates)
        display_leader_dashboard(leader_extended, leader_extended_data, radar_chart_data)
        st.subheader("Decklist")
        col1, col2, col3 = st.columns([0.4, 0.5, 0.1])
        with col2:
            display_list_view(decklist_data, card_ids_filtered)
    else:
        st.warning(f"No data available for Leader {leader_id}")

