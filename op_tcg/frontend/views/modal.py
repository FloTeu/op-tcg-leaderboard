import logging

import streamlit as st

from op_tcg.backend.models.cards import OPTcgCardCatagory, ExtendedCardData
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.tournaments import TournamentDecklist

from op_tcg.frontend.utils.chart import create_card_leader_occurrence_stream_chart
from op_tcg.frontend.utils.extract import get_tournament_decklist_data, get_card_id_card_data_lookup
from op_tcg.frontend.utils.js import execute_js_file
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid
from op_tcg.frontend.utils.styles import execute_style_sheet
from op_tcg.frontend.views.card import display_card_attributes


@st.dialog("Card Detail", width="large")
def display_card_details_dialog(card_id: str, carousel_card_ids: list[str] = None):
    logging.warning(f"Open Card Detail Modal {card_id}")
    def normalize_data(chart_data: list[dict[str, int]]) -> dict[str, float]:
        def normalize_dict_values(input_dict):
            # Calculate the sum of all values in the dictionary
            total_sum = sum(input_dict.values())
            # Check if the total sum is zero to avoid division by zero
            if total_sum == 0:
                raise ValueError("The sum of the values in the dictionary is zero, cannot normalize.")
            # Create a new dictionary with normalized values
            normalized_dict = {key: round(value / total_sum, 2) for key, value in input_dict.items()}
            return normalized_dict

        for i, data_lines in enumerate(chart_data):
            values = list(data_lines.values())
            if len(values) == 0:
                continue
            chart_data[i] = normalize_dict_values(data_lines)

        return chart_data

    def get_most_occurring_leader_ids(chart_data: list[dict[str, int]]) -> list[str]:
        leader_id_to_highest_value = {}
        for chart_data_i in chart_data:
            for lid, occurrence in chart_data_i.items():
                if lid not in leader_id_to_highest_value:
                    leader_id_to_highest_value[lid] = occurrence
                elif leader_id_to_highest_value[lid] < occurrence:
                    leader_id_to_highest_value[lid] = occurrence
        return [k for k, v in sorted(leader_id_to_highest_value.items(), key=lambda item: item[1], reverse=True)]

    index_offset = st.session_state.get("card_details_index_offset", 0)
    if index_offset == 0:
        # ensure index_offset is initialized
        st.session_state["card_details_index_offset"] = 0

    if index_offset != 0 and carousel_card_ids:
        card_index = carousel_card_ids.index(card_id) + index_offset
        card_id = carousel_card_ids[card_index]

    selected_card_id = card_id
    button_left, button_right = st.columns(2)
    if carousel_card_ids and card_id in carousel_card_ids:
        card_index = carousel_card_ids.index(card_id)
        if card_index != 0 and button_left.button(":arrow_left:", key=f"open_prev_modal_button"):
            selected_card_id = carousel_card_ids[card_index - 1]
            st.session_state["card_details_index_offset"] -= 1
            if card_index == (len(carousel_card_ids)-1) and button_right.button(":arrow_right:", key=f"open_next_modal_button"):
                selected_card_id = carousel_card_ids[card_index + 1]
                st.session_state["card_details_index_offset"] += 1
        if card_index != (len(carousel_card_ids)-1) and button_right.button(":arrow_right:", key=f"open_next_modal_button"):
            selected_card_id = carousel_card_ids[card_index + 1]
            st.session_state["card_details_index_offset"] += 1
            if card_index == 0 and button_left.button(":arrow_left:", key=f"open_prev_modal_button"):
                selected_card_id = carousel_card_ids[card_index - 1]
                st.session_state["card_details_index_offset"] -= 1


    with st.spinner():
        cid2card_data: dict[str, ExtendedCardData] = get_card_id_card_data_lookup(aa_version=0)
        card_data = cid2card_data[selected_card_id]
        chart_data, chart_data_meta_formats = get_stream_leader_occurrence_data(cid2card_data, selected_card_id)

        # filter top n most occurring leaders
        top_n_leaders = 5
        most_occurring_leader_ids = get_most_occurring_leader_ids(chart_data)[:top_n_leaders]
        chart_data = [{lid: occ for lid, occ in cd.items() if lid in most_occurring_leader_ids} for cd in chart_data]

        # display data
        col1, col2 = st.columns([0.7, 1])
        col1.image(card_data.image_url, use_container_width=True)
        with col2:
            display_card_attributes(card_data)

        show_normalized = st.toggle("Show normalized data", True)
        if show_normalized:
            try:
                chart_data = normalize_data(chart_data)
            except Exception as e:
                st.error("Sorry something went wrong with the data normalization")

        create_card_leader_occurrence_stream_chart(chart_data, x_tick_labels=chart_data_meta_formats, title=f"Occurrence in Top {top_n_leaders} Leader Decks")


    # center buttons (and other columns, which is not intended right now)
    execute_style_sheet("st_columns/two_cols_centered")
    execute_js_file("st_columns_prevent_mobile_break_button")


def get_stream_leader_occurrence_data(cid2card_data: dict[str, ExtendedCardData], card_id: str):
    # load data
    card_data = cid2card_data[card_id]
    release_meta = card_data.meta_format
    # start at least with OP02, since OP01 has no match data
    start_meta = release_meta if release_meta != MetaFormat.OP01 else MetaFormat.OP02
    meta_formats = MetaFormat.to_list()[MetaFormat.to_list().index(start_meta):]
    # display only the last n meta formats
    meta_formats = meta_formats[-10:]
    leaders_of_same_color = {cid: cdata for cid, cdata in cid2card_data.items() if
                             cdata.card_category == OPTcgCardCatagory.LEADER and any(
                                 c in cdata.colors for c in card_data.colors)}
    lid_to_name_lid_lookup = {lid: lid_to_name_and_lid(lid, leader_name=cid2card_data[lid].name) for lid in
                              leaders_of_same_color.keys()}
    decklist_data: list[TournamentDecklist] = get_tournament_decklist_data(meta_formats, leader_ids=list(
        leaders_of_same_color.keys()))
    init_lid2card_occ_dict = {lid: 0 for lid in leaders_of_same_color.keys()}
    meta_leader_id2card_occurrence_count: dict[MetaFormat, dict[str, int]] = {mf: init_lid2card_occ_dict.copy() for mf
                                                                              in meta_formats}
    for ddata in decklist_data:
        if ddata.meta_format in meta_leader_id2card_occurrence_count and card_id in ddata.decklist:
            meta_leader_id2card_occurrence_count[ddata.meta_format][ddata.leader_id] += 1
    chart_data_meta_formats = list(meta_leader_id2card_occurrence_count.keys())
    chart_data = [{lid_to_name_lid_lookup[lid]: card_occ for lid, card_occ in lid2card_occ_dict.items() if card_occ > 0}
                  for _, lid2card_occ_dict in meta_leader_id2card_occurrence_count.items()]
    return chart_data, chart_data_meta_formats
