import time
from datetime import date, datetime, timedelta
from functools import partial

import pandas as pd
import numpy as np
import streamlit as st

from contextlib import suppress
from pydantic import BaseModel
from streamlit.errors import StreamlitDuplicateElementId
from streamlit_elements import elements, mui

from op_tcg.backend.models.cards import ExtendedCardData, CardCurrency, LatestCardPrice
from op_tcg.backend.models.input import MetaFormat, meta_format2release_datetime, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.backend.models.tournaments import TournamentDecklist, TournamentExtended
from op_tcg.frontend.sidebar import display_leader_select, display_meta_select, display_only_official_toggle, \
    display_meta_format_region
from op_tcg.frontend.sub_pages.constants import SUB_PAGE_LEADER, Q_PARAM_EASIEST_OPPONENT, Q_PARAM_HARDEST_OPPONENT, \
    Q_PARAM_LEADER_ID, Q_PARAM_META
from op_tcg.frontend.sub_pages.utils import sub_page_title_to_url_path
from op_tcg.frontend.utils.chart import create_leader_line_chart, LineChartYValue, create_leader_win_rate_radar_chart, \
    get_radar_chart_data, create_line_chart, get_fillup_meta_formats, create_time_range_chart, TimeRangeValue
from op_tcg.frontend.utils.decklist import DecklistData, tournament_standings2decklist_data, \
    decklist_data_to_card_ids, get_most_similar_leader_data, SimilarLeaderData, \
    DecklistFilter, filter_tournament_decklists, get_best_matching_decklist
from op_tcg.frontend.utils.extract import get_leader_extended, get_leader_win_rate, get_tournament_decklist_data, \
    get_card_id_card_data_lookup, get_all_tournament_extened_data
from op_tcg.frontend.utils.js import is_mobile
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid, get_win_rate_dataframes, \
    get_lid2ldata_dict_cached
from op_tcg.frontend.utils.material_ui_fns import display_table, create_image_cell
from op_tcg.frontend.utils.query_params import get_default_leader_name, \
    delete_query_param, add_query_param
from op_tcg.frontend.utils.styles import read_style_sheet, css_rule_to_dict
from op_tcg.frontend.utils.utils import sort_df_by_meta_format
from op_tcg.frontend.views.decklist import display_list_view, display_decklist


class Matchup(BaseModel):
    leader_id: str
    win_rate: float
    total_matches: int
    meta_formats: list[MetaFormat]
    win_rate_chart_data: dict[MetaFormat, float]


class OpponentMatchups(BaseModel):
    easiest_matchups: list[Matchup]
    hardest_matchups: list[Matchup]


class DecklistPrices(BaseModel):
    prices_eur: list[float]
    prices_usd: list[float]


def add_qparam_on_change_fn(qparam2session_key: dict[str, str], reset_query_params: bool = False):
    for qparam, session_key in qparam2session_key.items():
        if qparam in [Q_PARAM_LEADER_ID, Q_PARAM_EASIEST_OPPONENT, Q_PARAM_HARDEST_OPPONENT]:
            qparam_value: str = lname_and_lid_to_lid(st.session_state.get(session_key, ""))
            add_query_param(qparam, qparam_value)
        else:
            add_query_param(qparam, st.session_state.get(session_key, ""))
    if reset_query_params:
        delete_query_param(Q_PARAM_EASIEST_OPPONENT)
        delete_query_param(Q_PARAM_HARDEST_OPPONENT)


def get_img_with_href(img_url, target_url):
    html_code = f'''
        <a href="{target_url}" target="_self" >
            <img src="{img_url}" />
        </a>'''
    return html_code


def get_leader_data(matchups: list[Matchup], leader_extended_data: list[LeaderExtended], q_param: str,
                    blacklist_lids: list[str] | None = None) -> LeaderExtended | None:
    blacklist_lids = blacklist_lids or []
    selected_opponent_id: str = lname_and_lid_to_lid(
        get_default_leader_name([m.leader_id for m in matchups if m.leader_id not in blacklist_lids],
                                query_param=q_param))
    opponent_data: LeaderExtended | None = None
    # Note: The exception might occurs if a leader is not complete yet (e.g. missing elo data)
    with suppress(Exception):
        opponent_data = list(filter(lambda le: le.id == selected_opponent_id, leader_extended_data))[0]
    return opponent_data


def display_leader_dashboard(leader_data: LeaderExtended, leader_extended_data: list[LeaderExtended], radar_chart_data,
                             tournament_decklists: list[TournamentDecklist], tournaments: list[TournamentExtended],
                             opponent_matchups: OpponentMatchups,
                             lid2similar_leader_data: dict[str, SimilarLeaderData]):
    cid2cdata_dict = get_card_id_card_data_lookup()

    avg_price_eur = np.mean([td.price_eur for td in tournament_decklists])
    avg_price_usd = np.mean([td.price_usd for td in tournament_decklists])
    meta_formats = [td.meta_format for td in tournament_decklists]
    min_tournament_date = min(td.tournament_timestamp for td in tournament_decklists).date() if len(
        tournament_decklists) > 0 else None

    hardest_opponent_data: LeaderExtended | None = get_leader_data(opponent_matchups.hardest_matchups,
                                                                   leader_extended_data,
                                                                   q_param=Q_PARAM_HARDEST_OPPONENT)
    easiest_opponent_data: LeaderExtended | None = get_leader_data(opponent_matchups.easiest_matchups,
                                                                   leader_extended_data,
                                                                   q_param=Q_PARAM_EASIEST_OPPONENT,
                                                                   blacklist_lids=[hardest_opponent_data.id])
    # remove selected easiest opponent data from hardest matchups and vice versa
    if hardest_opponent_data:
        opponent_matchups.easiest_matchups = [m for m in opponent_matchups.easiest_matchups if
                                              m.leader_id != hardest_opponent_data.id]
    if easiest_opponent_data:
        opponent_matchups.hardest_matchups = [m for m in opponent_matchups.hardest_matchups if
                                              m.leader_id != easiest_opponent_data.id]
    if (easiest_opponent_data and hardest_opponent_data) and (easiest_opponent_data.id == hardest_opponent_data.id):
        st.error("Selected best and worst opponent cannot be the same")
        return None

    col1, col2, col3 = st.columns([0.25, 0.05, 0.5])
    with col1:
        st.markdown("")
        st.image(leader_data.aa_image_url)
        st.markdown(f"""
**Average Price**: {'%.2f' % avg_price_eur}€ | ${'%.2f' % avg_price_usd}
""")
    with col3:
        st.subheader("Win Rate Chart")
        rounder_corners_css = css_rule_to_dict(read_style_sheet("chart", selector=".rounded-corners"))
        styles = {"height": 150,
                  **rounder_corners_css,
                  }
        create_leader_line_chart(leader_id=leader_data.id, leader_extended=leader_extended_data,
                                 enable_x_axis=True, enable_y_axis=False,
                                 y_value=LineChartYValue.WIN_RATE, styles=styles, auto_fillup=True)

        st.subheader("Win Rate Matchup")
        styles = {"height": 250,
                  **rounder_corners_css,
                  }
        create_leader_win_rate_radar_chart(radar_chart_data, [leader_data.id],
                                           colors=[leader_data.to_hex_color()], styles=styles)

    tab1, tab2, tab3 = st.tabs(["Opponents", "Decklist", "Tournaments"])
    with tab1:
        col1, col2, col3 = st.columns([0.3, 0.3, 0.3])
        with col1:
            if easiest_opponent_data:
                display_opponent_view(easiest_opponent_data.id, opponent_matchups.easiest_matchups,
                                      leader_extended_data, best_matchup=True)
            else:
                st.warning("Easiest opponent is not yet available")
        with col2:
            st.subheader("Win Rate Matchup")
            styles = {"height": 300,
                      **rounder_corners_css
                      }
            radar_chart_ids = [leader_data.id]
            radar_chart_colors = [leader_data.to_hex_color()]
            if hardest_opponent_data:
                radar_chart_ids.append(hardest_opponent_data.id)
                radar_chart_colors.append(hardest_opponent_data.to_hex_color())
            if easiest_opponent_data:
                radar_chart_ids.append(easiest_opponent_data.id)
                radar_chart_colors.append(easiest_opponent_data.to_hex_color())
            create_leader_win_rate_radar_chart(radar_chart_data, radar_chart_ids,
                                               colors=radar_chart_colors,
                                               styles=styles)
        with col3:
            if hardest_opponent_data:
                display_opponent_view(hardest_opponent_data.id, opponent_matchups.hardest_matchups,
                                      leader_extended_data, best_matchup=False)
            else:
                st.warning("Hardest opponent is not yet available")
    with tab2:
        col1, col2 = st.columns([0.4, 0.5])

        with col1:
            display_decklist_list_view_fragment(tournament_decklists, cid2cdata_dict, meta_formats, leader_data.id,
                                                min_tournament_date)

        with col2:
            most_similar_leader_ids = sorted(lid2similar_leader_data,
                                             key=lambda k: lid2similar_leader_data[k].similarity_score, reverse=True)
            st.subheader("Most similar leader")

            opponent_leader_names = [lid_to_name_and_lid(lid) for lid in most_similar_leader_ids]
            selected_most_similar_lname = display_leader_select(available_leader_names=opponent_leader_names,
                                                                key=f"select_most_sim_lid",
                                                                multiselect=False,
                                                                default=lid_to_name_and_lid(most_similar_leader_ids[0])
                                                                )
            selected_most_similar_lid = lname_and_lid_to_lid(selected_most_similar_lname)
            similar_leader_data = lid2similar_leader_data[selected_most_similar_lid]

            lid2data_dict = get_lid2ldata_dict_cached()
            col2_1, col2_2 = st.columns([0.4, 0.5])
            with col2_1:
                img_with_href = get_img_with_href(lid2data_dict[selected_most_similar_lid].aa_image_url,
                                                  f'/{sub_page_title_to_url_path(SUB_PAGE_LEADER)}?lid={selected_most_similar_lid}')
                st.markdown(img_with_href, unsafe_allow_html=True)
            with col2_2:
                cards_missing_price_eur = sum([cid2cdata_dict.get(cid,
                                                                  LatestCardPrice.from_default()).latest_eur_price *
                                               similar_leader_data.card_id2avg_count_card[cid] for cid in
                                               similar_leader_data.cards_missing])
                cards_missing_price_usd = sum([cid2cdata_dict.get(cid,
                                                                  LatestCardPrice.from_default()).latest_usd_price *
                                               similar_leader_data.card_id2avg_count_card[cid] for cid in
                                               similar_leader_data.cards_missing])

                cards_intersection_price_eur = sum([cid2cdata_dict.get(cid,
                                                                       LatestCardPrice.from_default()).latest_eur_price *
                                                    similar_leader_data.card_id2avg_count_card[cid] for cid in
                                                    similar_leader_data.cards_intersection])
                cards_intersection_price_usd = sum([cid2cdata_dict.get(cid,
                                                                       LatestCardPrice.from_default()).latest_usd_price *
                                                    similar_leader_data.card_id2avg_count_card[cid] for cid in
                                                    similar_leader_data.cards_intersection])

                st.markdown(f"""  
                **Deck Similarity**: {int(round(similar_leader_data.similarity_score, 2) * 100)}%
                
                **Missing Cards Price**: {f"{round(cards_missing_price_eur, 2)}".replace(".", ",")}€ | ${round(cards_missing_price_usd, 2)}
                
                **Intersection Cards Price**: {f"{round(cards_intersection_price_eur, 2)}".replace(".", ",")}€ | ${round(cards_intersection_price_usd, 2)}  
                """)

            display_cards_view(similar_leader_data.cards_intersection, cid2cdata_dict, title="Cards in both decks:")
            display_cards_view(similar_leader_data.cards_missing, cid2cdata_dict, title="Missing cards:")

    with tab3:
        display_tournament_view(leader_data.id, tournament_decklists, tournaments, cid2cdata_dict)


@st.fragment
def display_tournament_view(leader_id: str, tournament_decklists: list[TournamentDecklist],
                            tournaments: list[TournamentExtended], cid2cdata_dict):
    def _get_tournament_share(placings: list[int], num_players: int | None) -> float:
        if num_players is None:
            return 0
        return len(placings) / num_players

    st.subheader("Tournaments")
    meta_format_region: MetaFormatRegion = display_meta_format_region(multiselect=False)[0]
    tournament_ids: list[str] = []
    day_count: dict[date, int] = {}
    for td in tournament_decklists:
        if meta_format_region != MetaFormatRegion.ALL and td.meta_format_region != meta_format_region:
            continue
        elif td.placing != 1:
            continue
        elif not isinstance(td.tournament_timestamp, datetime):
            continue

        tournament_ids.append(td.tournament_id)
        t_date = td.tournament_timestamp.date()
        if t_date in day_count:
            day_count[t_date] += 1
        else:
            day_count[t_date] = 1

    tournaments_with_win = []
    for t in tournaments:
        if meta_format_region != MetaFormatRegion.ALL and t.meta_format_region != meta_format_region:
            continue
        if leader_id not in t.leader_ids_placings:
            continue
        elif 1 not in t.leader_ids_placings[leader_id]:
            continue
        tournaments_with_win.append(t)

    data = [TimeRangeValue(day=day_date, value=count) for day_date, count in day_count.items()]
    st.write("#### Tournament Wins")
    st.write(f"""
    In total: {len(tournaments_with_win)}
""")
    if len(data) == 0:
        st.warning("No tournament wins found")
    else:
        create_time_range_chart(data)
        selected_tournament_name = st.selectbox("Tournament", [t.name for t in tournaments_with_win])
        selected_tournament = [t for t in tournaments_with_win if t.name == selected_tournament_name][0]
        st.write(f"""
    Name: {selected_tournament.name}  {f'''
    Host: {selected_tournament.host}  ''' if selected_tournament.host else ""}{f'''
    Country: {selected_tournament.country}  ''' if selected_tournament.host else ""}
    Number Players: {selected_tournament.num_players if selected_tournament.num_players else "unknown"}  
    Winner: {cid2cdata_dict[leader_id].name} ({leader_id})  
    Date: {selected_tournament.tournament_timestamp.date() if isinstance(selected_tournament.tournament_timestamp, datetime) else "unknown"} 
        """)

        lid2tournament_share = {lid: _get_tournament_share(placings, selected_tournament.num_players) for lid, placings in
                                selected_tournament.leader_ids_placings.items()}
        lid2tournament_share_sorted = dict(sorted(lid2tournament_share.items(), key=lambda item: item[1], reverse=True))

        display_tournament_participants(lid2tournament_share_sorted, cid2cdata_dict)


def display_tournament_participants(lid2tournament_share_sorted, cid2cdata_dict):
    st.write("###### Participating leaders")
    st.info("The percentage represents the share of the leader in relation to the number of participants in the tournament")
    with elements("leader_images"):
        def _get_table_cell(lid: str, tournament_share: float):
            cdata = cid2cdata_dict[lid]
            img_url = cdata.image_url
            overlay_color = cdata.to_hex_color()
            text = "" if tournament_share == 0 else f"{(float('%.4f' % tournament_share) * 100)}"[:5] + "%"
            return create_image_cell(img_url, text=text, overlay_color=overlay_color, sx={
                'backgroundPosition': 'bottom, center -26px',
                'height': '160px'
            })

        cols = 4
        df_dict = {f"col_{i}": [] for i in range(cols)}
        for i, (lid, share) in enumerate(lid2tournament_share_sorted.items()):
            col = f"col_{i % cols}"
            df_dict[col].append(_get_table_cell(lid, share))
        last_added_col = int(col.split("_")[1])
        for j in range(cols):
            if j > last_added_col:
                df_dict[f"col_{j % cols}"].append(mui.TableCell(""))

        df = pd.DataFrame(df_dict)
        display_table(df, header_cells=[mui.TableCell("") for _ in range(df.shape[1])])


@st.fragment
def display_decklist_list_view_fragment(tournament_decklists: list[TournamentDecklist],
                                        cid2cdata_dict: dict[str, ExtendedCardData], meta_formats: list[MetaFormat],
                                        leader_id: str, min_tournament_date: date):
    st.subheader("Decklist")
    with st.expander("Decklist Filter"):
        decklist_filter: DecklistFilter = display_decklist_filter(tournament_decklists, meta_formats,
                                                                  min_tournament_date)
        tournament_decklists = filter_tournament_decklists(tournament_decklists, decklist_filter)
        decklist_data: DecklistData = tournament_standings2decklist_data(tournament_decklists,
                                                                         cid2cdata_dict)
    st.write(f"Number of decks: {decklist_data.num_decklists}")
    decklist_card_ids = decklist_data_to_card_ids(decklist_data, occurrence_threshold=0.02,
                                                  exclude_card_ids=[leader_id])
    display_list_view(decklist_data, decklist_card_ids)

    with st.expander("Decklists"):
        selected_matching_decklist = get_best_matching_decklist(tournament_decklists, decklist_data)
        if selected_matching_decklist:
            player_id = st.selectbox("Select Players Decklist", [td.player_id for td in tournament_decklists],
                                     index=None)
            if player_id:
                selected_matching_decklist = \
                    [td.decklist for td in tournament_decklists if td.player_id == player_id][0]
            if leader_id in selected_matching_decklist:
                selected_matching_decklist.pop(leader_id)
            display_decklist(selected_matching_decklist, is_mobile=is_mobile())
        else:
            st.warning("No decklists available. Please change the 'Start Date'")


def display_decklist_filter(tournament_decklists: list[TournamentDecklist], selected_meta_formats: list[MetaFormat],
                            decklist_min_tournament_date: date | None = None) -> DecklistFilter:
    oldest_release_date: date = datetime.now().date()
    for meta_format in selected_meta_formats:
        release_date = meta_format2release_datetime(meta_format)
        if release_date.date() < oldest_release_date:
            oldest_release_date = release_date.date()

    if decklist_min_tournament_date == None:
        min_date = oldest_release_date
    else:
        min_date = min(oldest_release_date, decklist_min_tournament_date)
    min_datetime = datetime(min_date.year, min_date.month, min_date.day)
    max_datetime = datetime(datetime.now().year, datetime.now().month, datetime.now().day) + timedelta(hours=23,
                                                                                                       minutes=59)

    filter_currency = st.selectbox("Currency", [CardCurrency.EURO, CardCurrency.US_DOLLAR])
    min_price = min(
        td.price_eur if filter_currency == CardCurrency.EURO else td.price_usd for td in tournament_decklists)
    max_price = max(
        td.price_eur if filter_currency == CardCurrency.EURO else td.price_usd for td in tournament_decklists)
    if min_price < max_price:
        selected_min_price, selected_max_price = st.slider("Decklist Price Range", min_price, max_price,
                                                           (min_price, max_price))
    else:
        selected_min_price, selected_max_price = min_price, max_price

    start_datetime, end_datetime = st.slider(
        "Date Range",
        min_value=min_datetime,
        max_value=max_datetime,
        value=(min_datetime, max_datetime),
        step=timedelta(days=1),
        format="DD/MM/YY",
        help="Format: DD/MM/YY")

    min_tournament_placing: int = st.number_input("Min Tournament Placing", value=None, min_value=1)

    return DecklistFilter(
        start_datetime=start_datetime,
        end_datetime=end_datetime,
        min_tournament_placing=min_tournament_placing,
        min_price=selected_min_price,
        max_price=selected_max_price,
        filter_currency=filter_currency
    )


def display_cards_view(card_ids: list[str], cid2cdata_dict: dict[str, ExtendedCardData], title: str, n_cols: int = 4):
    st.write(title)
    n_st_cols = st.columns([1 / n_cols for i in range(n_cols)])
    for i, card_id in enumerate(card_ids[:n_cols]):
        with n_st_cols[i % n_cols]:
            if card_id in cid2cdata_dict:
                st.image(cid2cdata_dict[card_id].image_url)
    with st.expander("show all cards"):
        n_st_cols = st.columns([1 / n_cols for i in range(n_cols)])
        for i, card_id in enumerate(card_ids[n_cols:]):
            with n_st_cols[i % n_cols]:
                if card_id in cid2cdata_dict:
                    st.image(cid2cdata_dict[card_id].image_url)


def display_opponent_view(selected_opponent_id: str, matchups: list[Matchup],
                          leader_extended_data: list[LeaderExtended], best_matchup: bool):
    if not any(m.leader_id == selected_opponent_id for m in matchups):
        st.warning(f"Selected opponent {selected_opponent_id} has no matchup data")
        return None
    opponent_index = next(i for i, obj in enumerate(matchups) if obj.leader_id == selected_opponent_id)
    opponent_matchup = matchups[opponent_index]
    opponent_leader_data = [le for le in leader_extended_data if le.id == opponent_matchup.leader_id][0]
    opponent_leader_names = [lid_to_name_and_lid(m.leader_id) for m in matchups]
    st.subheader(("Easiest" if best_matchup else "Hardest") + " Matchup")
    display_leader_select(available_leader_names=opponent_leader_names,
                          key=f"select_opp_lid_{selected_opponent_id}",
                          multiselect=False,
                          default=opponent_leader_names[opponent_index],
                          on_change=partial(add_qparam_on_change_fn, qparam2session_key={
                              Q_PARAM_EASIEST_OPPONENT if best_matchup else Q_PARAM_HARDEST_OPPONENT: f"select_opp_lid_{selected_opponent_id}"}),
                          )
    img_with_href = get_img_with_href(opponent_leader_data.aa_image_url,
                                      f'/{sub_page_title_to_url_path(SUB_PAGE_LEADER)}?lid={opponent_leader_data.id}')
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
        rounded_corners_css = css_rule_to_dict(read_style_sheet("chart", selector=".rounded-corners"))
        styles = {"height": 150,
                  **rounded_corners_css,
                  }
        with mui.Box():
            try:
                create_line_chart(opponent_matchup.win_rate_chart_data, data_id="WR", enable_x_axis=True,
                                  enable_y_axis=False, styles=styles,
                                  fillup_meta_formats=get_fillup_meta_formats(opponent_matchup.win_rate_chart_data),
                                  use_custom_component=True)
            except StreamlitDuplicateElementId:
                st.warning("Win rate chart could not be loaded")


def get_best_and_worst_opponent(df_meta_win_rate_data, meta_formats: list[MetaFormat],
                                exclude_leader_ids: list[str] | None = None) -> OpponentMatchups:
    def create_matchup(df_group, win_rate_chart_data) -> Matchup:
        return Matchup(
            leader_id=df_group.iloc[0]["opponent_id"],
            win_rate=df_group["win_rate"].mean(),
            meta_formats=df_group["meta_format"].to_list(),
            total_matches=df_group["total_matches"].sum(),
            win_rate_chart_data={meta: round(wr, 2) for meta, wr in win_rate_chart_data.items()},
        )

    exclude_leader_ids = exclude_leader_ids or []

    # sort dataframe
    df_meta_win_rate_data = sort_df_by_meta_format(df_meta_win_rate_data)
    leader_id2win_rate_chart_data: dict[str, dict[MetaFormat, float]] = df_meta_win_rate_data.groupby(
        "opponent_id").apply(
        lambda df_group: df_group[["meta_format", "win_rate"]].set_index("meta_format")["win_rate"].to_dict()).to_dict()
    # drop data not in selected meta format
    df_meta_win_rate_data = df_meta_win_rate_data.query("meta_format in @meta_formats")

    max_total_matches = df_meta_win_rate_data["total_matches"].max()
    # min 10 or 10% of the max total matches
    threshold = min(int(max_total_matches / 10), 10)
    df_sorted = df_meta_win_rate_data.query(f"total_matches > {threshold}").sort_values("win_rate")

    matchups: list[Matchup] = df_sorted.query("opponent_id not in @exclude_leader_ids").groupby("opponent_id").apply(
        lambda df_group: create_matchup(df_group,
                                        leader_id2win_rate_chart_data[df_group.iloc[0]["opponent_id"]])).to_list()
    matchups.sort(key=lambda m: m.win_rate)
    worst_matchups = matchups.copy()
    matchups.sort(key=lambda m: m.win_rate, reverse=True)
    best_matchups = matchups.copy()
    return OpponentMatchups(easiest_matchups=best_matchups,
                            hardest_matchups=worst_matchups)


def main_leader_detail_analysis():
    with st.sidebar:
        selected_meta_formats: list[MetaFormat] = display_meta_select(multiselect=True,
                                                      default=st.query_params.get(Q_PARAM_META, None),
                                                      on_change=partial(add_qparam_on_change_fn,
                                                                       qparam2session_key={
                                                                           Q_PARAM_META: "selected_meta_format"}),
                                                      key="selected_meta_format")

    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
        return None

    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    available_leader_ids = list(
        dict.fromkeys([l.id for l in leader_extended_data if l.meta_format in selected_meta_formats]))
    if len(available_leader_ids) == 0:
        st.warning("No leader data available for the selected meta")
        return None
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids, query_param="lid")

    with st.sidebar:
        selected_leader_name: str = display_leader_select(available_leader_names=available_leader_names,
                                                          key="selected_lid",
                                                          multiselect=False, default=default_leader_name,
                                                          on_change=partial(add_qparam_on_change_fn,
                                                                            qparam2session_key={"lid": "selected_lid"},
                                                                            reset_query_params=True))
        only_official: bool = display_only_official_toggle()

    leader_extended = None
    if selected_leader_name:
        leader_id: str = lname_and_lid_to_lid(selected_leader_name)
        leader_extended_filtered = [le for le in leader_extended_data if
                                    le.meta_format in selected_meta_formats and le.id == leader_id and le.only_official == only_official]
        if len(leader_extended_filtered) > 0:
            leader_extended = leader_extended_filtered[0]

    st.header(f"Leader: {selected_leader_name}")
    if leader_extended:
        # get most similar leader ids
        t1 = time.time()
        lid2similar_leader_data: dict[str, SimilarLeaderData] = get_most_similar_leader_data(leader_extended.id,
                                                                                             selected_meta_formats,
                                                                                             threshold_occurrence=0.4)
        print("elapsed time %.2f" % (time.time() - t1))

        selected_meta_win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=MetaFormat.to_list())
        df_meta_win_rate_data = pd.DataFrame(
            [lwr.dict() for lwr in selected_meta_win_rate_data if lwr.only_official == only_official])

        opponent_matchups = get_best_and_worst_opponent(
            df_meta_win_rate_data.query(f"leader_id == '{leader_extended.id}'"), meta_formats=selected_meta_formats,
            exclude_leader_ids=[leader_extended.id])

        # Get decklist data
        tournament_decklists: list[TournamentDecklist] = get_tournament_decklist_data(
            meta_formats=selected_meta_formats, leader_ids=[leader_extended.id])
        # get tournament data
        tournaments: list[TournamentExtended] = get_all_tournament_extened_data(meta_formats=selected_meta_formats)
        # Get color matchup radar plot data
        leader_ids = list(
            set([leader_extended.id, *[matchup.leader_id for matchup in opponent_matchups.hardest_matchups],
                 *[matchup.leader_id for matchup in opponent_matchups.easiest_matchups]]))
        _, _, df_color_win_rates = get_win_rate_dataframes(
            df_meta_win_rate_data.query("meta_format in @selected_meta_formats"), leader_ids)
        radar_chart_data: list[dict[str, str | float]] = get_radar_chart_data(df_color_win_rates)

        display_leader_dashboard(leader_extended, leader_extended_data, radar_chart_data, tournament_decklists,
                                 tournaments, opponent_matchups, lid2similar_leader_data)
    else:
        st.warning(f"No data available for Leader {leader_id}")
