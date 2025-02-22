from collections import defaultdict
from functools import partial

import streamlit as st

from op_tcg.backend.models.cards import ExtendedCardData
from op_tcg.backend.models.tournaments import TournamentDecklist, TournamentExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.sub_pages.constants import Q_PARAM_LEADER_ID
from op_tcg.frontend.utils.chart import create_card_leader_occurrence_stream_chart
from op_tcg.frontend.utils.extract import get_leader_extended, get_tournament_decklist_data, \
    get_all_tournament_extened_data, get_card_id_card_data_lookup
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select, \
    display_meta_format_region
from op_tcg.frontend.utils.leader_data import lids_to_name_and_lids, lname_and_lid_to_lid, lid_to_name_and_lid

from streamlit_theme import st_theme

from op_tcg.frontend.utils.query_params import add_query_param, get_default_leader_names

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}


def add_qparam_on_change_fn(qparam2session_key: dict[str, str]):
    for qparam, session_key in qparam2session_key.items():
        if session_key == "selected_lids":
            selected_leader_names: list[str] = st.session_state[session_key]
            selected_leader_ids = [lname_and_lid_to_lid(lname) for lname in selected_leader_names]
            add_query_param(qparam, selected_leader_ids)
        else:
            raise NotImplementedError


def tournament_decklists_to_stream_data(tournament_decklists: list[TournamentDecklist], cumulative: bool = False):
    # dict[week information, dict[leader name, tournament wins]]
    stream_data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))
    cid2card_data: dict[str, ExtendedCardData] = get_card_id_card_data_lookup(aa_version=0)
    lid_to_name = {}

    for td in tournament_decklists:
        # Extract the calendar week and year from the tournament timestamp
        # Use ISO week date format to ensure week starts with 01
        week_info = td.tournament_timestamp.strftime('%V-%g')

        # Check if the placing is 1, indicating a tournament win
        if td.placing == 1:
            if td.leader_id not in lid_to_name:
                lid_to_name[td.leader_id] = lid_to_name_and_lid(td.leader_id,
                                                                leader_name=cid2card_data[td.leader_id].name)

            leader_name = lid_to_name[td.leader_id]
            stream_data[week_info][leader_name] += 1

    # Convert defaultdict to regular dict and sort by week information
    sorted_weeks = sorted(stream_data.items(), key=lambda x: (int(x[0].split('-')[1]), int(x[0].split('-')[0])))
    # sorted_weeks = sorted(stream_data.items(), key=lambda x: datetime.strptime(x[0] + '-1', '%U-%Y-%w'))
    sorted_stream_data = {week: dict(leaders) for week, leaders in sorted_weeks}

    if cumulative:
        # Accumulate the tournament wins over time
        cumulative_data = defaultdict(lambda: defaultdict(int))
        previous_week_data = defaultdict(int)

        for week, leaders in sorted_stream_data.items():
            for leader in set(previous_week_data.keys()).union(leaders.keys()):
                cumulative_data[week][leader] = previous_week_data[leader] + leaders.get(leader, 0)

            # Update previous_week_data for the next iteration
            previous_week_data.update(cumulative_data[week])

        sorted_stream_data = {week: dict(leaders) for week, leaders in cumulative_data.items()}

    return sorted_stream_data


@st.fragment
def display_tournament_leader_chart(tournament_decklists: list[TournamentDecklist]):
    if len(tournament_decklists) == 0:
        st.warning("No tournament decklists available")
        return None
    timestamps = [td.tournament_timestamp for td in tournament_decklists]
    min_date = min(timestamps)
    max_date = max(timestamps)
    selected_min_date, selected_max_date = st.slider(
        "Select date range",
        min_value=min_date,
        max_value=max_date,
        value=(min_date, max_date),
        format="YYYY-MM-DD"
    )
    tournament_decklists = [td for td in tournament_decklists if
                            td.tournament_timestamp >= selected_min_date and td.tournament_timestamp <= selected_max_date
                            ]

    stream_data = tournament_decklists_to_stream_data(tournament_decklists, cumulative=True)
    x_tick_labels = list(stream_data.keys())
    data = list(stream_data.values())
    create_card_leader_occurrence_stream_chart(data,
                                               x_tick_labels=x_tick_labels,
                                               offset_type="diverging",
                                               bottom_tick_rotation=-45,
                                               enable_y_axis=True,
                                               title="Tournament Wins by Leader")


def display_tournaments(tournaments: list[TournamentExtended], tournament_decklists: list[TournamentDecklist]) -> None:
    display_tournament_leader_chart(tournament_decklists)


def main_tournaments():
    st.header("Tournaments")

    with st.sidebar:
        selected_meta_formats: list[MetaFormat] = display_meta_select(multiselect=True)
        meta_format_region: MetaFormatRegion = display_meta_format_region(multiselect=False)[0]
        only_official = False
        # only_official: bool = display_only_official_toggle()
    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
        return None

    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    # first element is leader with best d_score
    leader_extended_data = list(
        filter(lambda x: x.meta_format in selected_meta_formats,
               leader_extended_data))
    leader_extended_data.sort(key=lambda x: x.d_score, reverse=True)
    available_leader_ids = list(dict.fromkeys([le.id for le in leader_extended_data]))
    available_leader_names = lids_to_name_and_lids(available_leader_ids)

    with st.sidebar:
        default_leader_names = get_default_leader_names(available_leader_ids, query_param=Q_PARAM_LEADER_ID)
        if len(set(available_leader_names) - set(default_leader_names)) == 0:
            default_leader_names = default_leader_names[0:5]
        selected_leader_names: list[str] = display_leader_select(available_leader_names=available_leader_names,
                                                                 multiselect=True, default=default_leader_names,
                                                                 key="selected_lids",
                                                                 on_change=partial(add_qparam_on_change_fn,
                                                                                   qparam2session_key={
                                                                                       Q_PARAM_LEADER_ID: "selected_lids"}))

    if len(selected_leader_names) < 1:
        st.warning("Please select at least one leader")
        return None
    selected_leader_ids: list[str] = [lname_and_lid_to_lid(ln) for ln in selected_leader_names]

    # Get decklist data
    tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
        meta_formats=selected_meta_formats, leader_ids=selected_leader_ids)
    # get tournament data
    tournaments: list[TournamentExtended] = get_all_tournament_extened_data(meta_formats=selected_meta_formats)

    # filter by meta format region
    if meta_format_region != MetaFormatRegion.ALL:
        tournament_decklists = [td for td in tournament_decklists if td.meta_format_region == meta_format_region]
        tournaments = [t for t in tournaments if t.meta_format_region == meta_format_region]
    display_tournaments(tournaments, tournament_decklists)
