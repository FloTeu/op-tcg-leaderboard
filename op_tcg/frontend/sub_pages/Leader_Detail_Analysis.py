import streamlit as st
from streamlit_elements import elements, mui, dashboard, nivo, html as element_html

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.sidebar import display_leader_select
from op_tcg.frontend.utils.chart import create_leader_line_chart, LineChartYValue
from op_tcg.frontend.utils.extract import get_leader_extended
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param

st.write("Example chart for leader performance vs different colors")

def display_leader_dashboard(leader_data: LeaderExtended, leader_extended_data: list[LeaderExtended]):

    with elements("dashboard"):
        # Layout for every element in the dashboard

        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("leader_image", 0, 0, 2, 4, isDraggable=False, isResizable=False),
            dashboard.Item("leader_win_rate", 2, 0, 4, 1, isDraggable=False, isResizable=False),
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
            mui.Box(key="leader_win_rate", children=create_leader_line_chart(leader_id=leader_data.id, leader_extended=leader_extended_data, enable_x_axis=True, enable_y_axis=False, y_value=LineChartYValue.WIN_RATE))


def main_leader_detail_analysis():
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    available_leader_ids = list(dict.fromkeys([l.id for l in leader_extended_data]))
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids)

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
        display_leader_dashboard(leader_extended, leader_extended_data)
    else:
        st.warning(f"No data available for Leader {leader_id}")

