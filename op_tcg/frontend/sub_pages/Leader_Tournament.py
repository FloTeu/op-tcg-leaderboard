import pandas as pd
import streamlit as st
import plotly.express as px
import numpy as np

from collections import defaultdict
from dataclasses import dataclass, asdict
from functools import partial
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
from op_tcg.frontend.utils.js import dict_to_js_func, is_mobile
from op_tcg.frontend.utils.leader_data import lids_to_name_and_lids, lname_and_lid_to_lid, lid_to_name_and_lid

from streamlit_theme import st_theme

from op_tcg.frontend.utils.query_params import add_query_param, get_default_leader_names
from op_tcg.frontend.utils.styles import brighten_hex_color
from op_tcg.frontend.views.decklist import display_decklist, display_decklist_export
from op_tcg.frontend.views.tournament import display_tournament_keyfacts

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}

@dataclass
class TournamentBubbleData:
    leader_id: str
    leader_name: str
    leader_image: str
    color_name: str
    color_hex: str
    tournament_wins: list[int]
    win_rate: list[float]
    total_matches: list[int]

    def to_pd_row_dict(self) -> dict:
        d_dict = asdict(self)
        d_dict["tournament_wins"] = sum(d_dict["tournament_wins"])
        valid_win_rates = [wr for wr in d_dict["win_rate"] if wr != 0]
        if len(valid_win_rates) > 0:
            d_dict["win_rate"] = sum(valid_win_rates) / len(valid_win_rates)
        else:
            d_dict["win_rate"] = 0
        d_dict["total_matches"] = sum(d_dict["total_matches"])
        return d_dict


def add_qparam_on_change_fn(qparam2session_key: dict[str, str]):
    for qparam, session_key in qparam2session_key.items():
        if session_key == "selected_lids":
            selected_leader_names: list[str] = st.session_state[session_key]
            selected_leader_ids = [lname_and_lid_to_lid(lname) for lname in selected_leader_names]
            add_query_param(qparam, selected_leader_ids)
        else:
            raise NotImplementedError


def tournament_decklists_to_stream_data(tournament_decklists: list[TournamentDecklist],
                                        lid_to_name: dict[str, str],
                                        cumulative: bool = False):
    # dict[week information, dict[leader name, tournament wins]]
    stream_data: dict[str, dict[str, int]] = defaultdict(lambda: defaultdict(int))

    for td in tournament_decklists:
        # Extract the calendar week and year from the tournament timestamp
        # Use ISO week date format to ensure week starts with 01
        week_info = td.tournament_timestamp.strftime('%V-%g')

        # Check if the placing is 1, indicating a tournament win
        if td.placing == 1:
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

def tournament_decklists_to_bubble_data(leader_extended_data: list[LeaderExtended]) -> list[TournamentBubbleData]:
    lid_to_bubble_data: dict[str, TournamentBubbleData] = {}
    for led in leader_extended_data:
        if led.id not in lid_to_bubble_data:
            lid_to_bubble_data[led.id] = TournamentBubbleData(
                leader_id=led.id,
                leader_image=led.aa_image_url,
                leader_name=lid_to_name_and_lid(led.id, leader_name=led.name),
                color_name=",".join(led.colors),
                color_hex=led.to_hex_color(),
                tournament_wins=[led.tournament_wins],
                win_rate=[led.win_rate],
                total_matches=[led.total_matches]
            )
        else:
            lid_to_bubble_data[led.id].tournament_wins.append(led.tournament_wins)
            lid_to_bubble_data[led.id].win_rate.append(led.win_rate)
            lid_to_bubble_data[led.id].total_matches.append(led.total_matches)

    return list(lid_to_bubble_data.values())

@st.fragment
def display_tournament_leader_chart(tournament_decklists: list[TournamentDecklist], cid2card_data, available_leader_ids: list[str]):
    if len(tournament_decklists) == 0:
        st.warning("No tournament decklists available")
        return None

    col1, col2 = st.columns((0.3,0.7))
    timestamps = [td.tournament_timestamp for td in tournament_decklists]
    min_date = min(timestamps)
    max_date = max(timestamps)
    with col1:
        selected_min_date, selected_max_date = col1.slider(
            "Select date range",
            min_value=min_date,
            max_value=max_date,
            value=(min_date, max_date),
            format="YYYY-MM-DD"
        )

        available_leader_names = lids_to_name_and_lids(available_leader_ids)
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

    tournament_decklists = [td for td in tournament_decklists if
                                (td.tournament_timestamp >= selected_min_date and
                                 td.tournament_timestamp <= selected_max_date and
                                 td.leader_id in selected_leader_ids
                                 )
                            ]
    lid_to_name = {}
    lname_to_color = {}
    for td in tournament_decklists:
        if td.leader_id not in lid_to_name:
            lname = lid_to_name_and_lid(td.leader_id, leader_name=cid2card_data[td.leader_id].name)
            lid_to_name[td.leader_id] = lname
            color = cid2card_data[td.leader_id].to_hex_color()
            while color in lname_to_color.values():
                color = brighten_hex_color(color, factor=1.5)
            lname_to_color[lname] = color


    stream_data = tournament_decklists_to_stream_data(tournament_decklists, lid_to_name, cumulative=True)
    x_tick_labels = list(stream_data.keys())
    data = list(stream_data.values())
    colors = dict_to_js_func(lname_to_color, default_value="#ff0000")

    with col2:
        with st.spinner():
            create_card_leader_occurrence_stream_chart(data,
                                               x_tick_labels=x_tick_labels,
                                               offset_type="diverging",
                                               bottom_tick_rotation=-45,
                                               enable_y_axis=True,
                                               legend_translate_x=0 if is_mobile() else 100,
                                               colors=colors,
                                               title="Tournament Wins")

@st.fragment
def display_tournament_bubble_chart(leader_extended_data: list[LeaderExtended]):
    st.subheader("Leader Popularity", help="Size of the bubbles increases with the tournament wins")
    bubble_data = tournament_decklists_to_bubble_data(leader_extended_data)
    df = pd.DataFrame([bd.to_pd_row_dict() for bd in bubble_data])

    # Calculate the size (tournament_wins) with a minimum value
    min_size = 1  # Minimum size for points with tournament_wins == 0
    df['size'] = df['tournament_wins'] + min_size

    # Get unique color names and their corresponding colors
    unique_colors = df[['color_name', 'color_hex']].drop_duplicates()
    color_dict = dict(zip(unique_colors['color_name'], unique_colors['color_hex']))

    # Create a new figure
    fig = px.scatter(df, x="total_matches", y="win_rate",
                     size="size", color="color_name",
                     hover_name="leader_name", log_x=True, size_max=40 if is_mobile() else 80)

    # Update each trace with the correct color from the color_hex column
    for trace in fig.data:
        color_name = trace.name
        hex_color = color_dict[color_name]
        mask = df['color_name'] == color_name
        fig.update_traces(marker=dict(color=list(df[mask]['color_hex'].values)),
                          selector={'name': color_name})

    # Customize the hover information
    for i, trace in enumerate(fig.data):
        mask = df['color_name'] == trace.name
        filtered_df = df[mask]
        custom_data = np.stack((filtered_df['leader_name'],
                                filtered_df['tournament_wins'],
                                filtered_df['total_matches'],
                                filtered_df['leader_image']), axis=1)

        fig.update_traces(hovertemplate=
                          "<b> %{customdata[0]} </b><br>" +
                          "Win Rate: %{y}<br>" +
                          "Tournament Wins: %{customdata[1]}<br>" +
                          "Total Matches: %{x}<br>",
                          customdata=custom_data,
                          selector={'name': trace.name})

    # Update the layout
    fig.update_layout(
        xaxis_title="Total Matches",
        yaxis_title="Win Rate",
        xaxis=dict(type="log"),
        showlegend=False)

    st.plotly_chart(fig)


@st.fragment
def display_latest_tournament(tournaments: list[TournamentExtended], tournament_decklists: list[TournamentDecklist], cid2card_data) -> None:
    st.subheader("Latest Tournaments")
    col1, _, col2 = st.columns((0.2, 0.1, 0.8))

    tid_to_decklists = {}
    for td in tournament_decklists:
        if td.tournament_id not in tid_to_decklists:
            tid_to_decklists[td.tournament_id] = [td]
        else:
            tid_to_decklists[td.tournament_id].append(td)

    tournaments_with_decklists = [t for t in tournaments if t.id in tid_to_decklists]

    with col1:
        selected_tournament_name = st.selectbox("Tournament", [t.name for t in tournaments_with_decklists])
    selected_tournament = [t for t in tournaments_with_decklists if t.name == selected_tournament_name][0]

    winner_decklist: TournamentDecklist = None
    winner_leader_name = "Not Known"
    winner_decklists = [td for td in tid_to_decklists[selected_tournament.id] if td.placing == 1]
    if len(winner_decklists) == 0:
        st.warning("No winner decklist available")
    else:
        winner_decklist = winner_decklists[0]
    if winner_decklist:
        winner_leader_name = lid_to_name_and_lid(winner_decklist.leader_id, leader_name=cid2card_data[winner_decklist.leader_id].name)
    with col1:
        st.markdown("#### Facts")
        display_tournament_keyfacts(selected_tournament, winner_name=winner_leader_name)
        if winner_decklist:
            st.markdown(f"##### Winner {winner_leader_name}")
            st.image(cid2card_data[winner_decklist.leader_id].image_url)
    with col2:
        st.markdown("#### Tournament Decklists")
        st.markdown("")
        available_decklists = {td.placing: td for td in tid_to_decklists[selected_tournament.id] if td.placing}
        available_placings = list(available_decklists.keys())
        available_placings.sort()
        placing = st.selectbox("Tournament placing", available_placings)
        selected_decklist = available_decklists[placing]
        lname = lid_to_name_and_lid(selected_decklist.leader_id, leader_name=cid2card_data[selected_decklist.leader_id].name)
        st.markdown(f"##### Selected Decklist: {lname}")
        decklist_dict = selected_decklist.decklist
        if selected_decklist.leader_id in decklist_dict:
            decklist_dict.pop(selected_decklist.leader_id)
        display_decklist(decklist_dict, is_mobile=is_mobile())
        display_decklist_export(selected_decklist.decklist, selected_decklist.leader_id)


def display_tournaments(tournaments: list[TournamentExtended], tournament_decklists: list[TournamentDecklist], leader_extended_data: list[LeaderExtended], cid2card_data, available_leader_ids) -> None:
    display_tournament_leader_chart(tournament_decklists, cid2card_data, available_leader_ids)
    display_tournament_bubble_chart(leader_extended_data)
    display_latest_tournament(tournaments, tournament_decklists, cid2card_data)


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

    leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=meta_format_region)
    # first element is leader with best d_score
    leader_extended_data = list(
        filter(lambda x: x.meta_format in selected_meta_formats,
               leader_extended_data))
    leader_extended_data.sort(key=lambda x: x.d_score, reverse=True)
    available_leader_ids = list(dict.fromkeys([le.id for le in leader_extended_data]))

    def filter_fn(le: LeaderExtended) -> bool:
        keep_le = le.only_official == only_official
        # filter match_count
        if selected_meta_formats:
            keep_le = keep_le and (le.meta_format in selected_meta_formats)
        return keep_le

    # run filters
    leader_extended_data = list(filter(lambda x: filter_fn(x), leader_extended_data))


    # Get decklist data
    tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
        meta_formats=selected_meta_formats)
    # get tournament data
    tournaments: list[TournamentExtended] = get_all_tournament_extened_data(meta_formats=selected_meta_formats)
    # get card data
    cid2card_data: dict[str, ExtendedCardData] = get_card_id_card_data_lookup(aa_version=0)

    # filter by meta format region
    if meta_format_region != MetaFormatRegion.ALL:
        tournament_decklists = [td for td in tournament_decklists if td.meta_format_region == meta_format_region]
        tournaments = [t for t in tournaments if t.meta_format_region == meta_format_region]
    display_tournaments(tournaments, tournament_decklists, leader_extended_data, cid2card_data, available_leader_ids)
