from datetime import datetime, date, timedelta

import streamlit as st
from statistics import mean

from op_tcg.backend.models.input import MetaFormat, meta_format2release_datetime
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.cards import OPTcgLanguage, CardCurrency
from op_tcg.backend.models.tournaments import TournamentStanding, TournamentStandingExtended
from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select
from op_tcg.frontend.sub_pages.constants import Q_PARAM_LEADER_ID
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data, DecklistData, get_best_matching_decklist
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.extract import get_tournament_standing_data, get_leader_extended, \
    get_card_id_card_data_lookup
from op_tcg.frontend.utils.js import is_mobile
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid

from op_tcg.frontend.views.decklist import display_list_view, display_decklist


@timeit
def main_leader_detail_analysis_decklists():
    st.header("Leader Decklist")

    with st.sidebar:
        selected_meta_formats: list[MetaFormat] = display_meta_select(multiselect=True)

    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
    else:

        leader_extended_data: list[LeaderExtended] = get_leader_extended()
        available_leader_ids = list(
            dict.fromkeys([l.id for l in leader_extended_data if l.meta_format in selected_meta_formats]))
        if len(available_leader_ids) == 0:
            st.warning("No leader data available for the selected meta")
            return None
        available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
        default_leader_name = get_default_leader_name(available_leader_ids)
        with st.sidebar:
            selected_leader_name: str = display_leader_select(available_leader_names=available_leader_names, key="select_lid",
                                                              multiselect=False, default=default_leader_name,
                                                              on_change=lambda: add_query_param(Q_PARAM_LEADER_ID, lname_and_lid_to_lid(st.session_state.get("select_lid", "")))
                                                              )
            oldest_release_data: date = datetime.now().date()
            oldest_release_datetime: datetime = datetime.now()
            for meta_format in selected_meta_formats:
                release_date = meta_format2release_datetime(meta_format)
                if release_date.date() < oldest_release_data:
                    oldest_release_data = release_date.date()
                    oldest_release_datetime = release_date

        if selected_leader_name:
            leader_id: str = lname_and_lid_to_lid(selected_leader_name)
            # TODO: Try using get_tournament_decklist_data instead
            tournament_standings: list[TournamentStandingExtended] = get_tournament_standing_data(
                meta_formats=selected_meta_formats, leader_id=leader_id)
            if len(tournament_standings) == 0:
                st.warning("No decklist data available for the selected meta and leader")
                return None
            card_id2card_data = get_card_id_card_data_lookup()
            decklist_id2price_eur = {
                (ts.id, ts.player_id): get_decklist_price(ts.decklist, card_id2card_data, currency=CardCurrency.EURO)
                for ts in tournament_standings if ts.decklist}
            decklist_id2price_usd = {(ts.id, ts.player_id): get_decklist_price(ts.decklist, card_id2card_data,
                                                                               currency=CardCurrency.US_DOLLAR) for ts
                                     in tournament_standings if ts.decklist}
            with st.sidebar:
                filter_currency = st.selectbox("Currency", [CardCurrency.EURO, CardCurrency.US_DOLLAR])
                min_price = min(decklist_id2price_eur.values()) if filter_currency == CardCurrency.EURO else min(
                    decklist_id2price_usd.values())
                max_price = max(decklist_id2price_eur.values()) if filter_currency == CardCurrency.EURO else max(
                    decklist_id2price_usd.values())
                if min_price < max_price:
                    selected_min_price, selected_max_price = st.slider("Decklist Price Range", min_price, max_price,
                                                                       (min_price, max_price))
                else:
                    selected_min_price, selected_max_price = min_price, max_price

                min_date = min(oldest_release_datetime.date(),
                    min([ts.tournament_timestamp.date() for ts in tournament_standings]))
                min_datetime = datetime(min_date.year, min_date.month, min_date.day)
                max_datetime = datetime(datetime.now().year, datetime.now().month, datetime.now().day)
                start_datetime, end_datetime = st.slider(
                    "Date Range",
                    min_value=min_datetime,
                    max_value=max_datetime,
                    value=(min_datetime, max_datetime),
                    step=timedelta(days=1),
                    format="DD/MM/YY",
                    help="Format: DD/MM/YY")

                min_tournament_placing: int = st.number_input("Min Tournament Placing", value=None, min_value=1)


            # filter by selected date and cost range
            def filter_tournament_standing(ts: TournamentStanding) -> bool:
                is_in_placing = (ts.placing <= min_tournament_placing if ts.placing and min_tournament_placing else True)
                if filter_currency == CardCurrency.EURO:
                    is_in_price = (
                            decklist_id2price_eur[ts.id, ts.player_id] >= selected_min_price and
                            decklist_id2price_eur[ts.id, ts.player_id] <= selected_max_price
                    )
                else:
                    is_in_price = (
                        decklist_id2price_usd[ts.id, ts.player_id] >= selected_min_price and
                        decklist_id2price_usd[ts.id, ts.player_id] <= selected_max_price
                    )
                return (
                    ts.tournament_timestamp.date() >= start_datetime.date() and
                    ts.tournament_timestamp.date() <= end_datetime.date() and
                    is_in_placing and
                    is_in_price

                )

            tournament_standings = [ts for ts in tournament_standings if filter_tournament_standing(ts)]
            decklist_id2price_eur = {(ts.id, ts.player_id): decklist_id2price_eur[ts.id, ts.player_id] for ts in
                                     tournament_standings}
            decklist_id2price_usd = {(ts.id, ts.player_id): decklist_id2price_usd[ts.id, ts.player_id] for ts in
                                     tournament_standings}
            if len(tournament_standings) == 0:
                st.warning("No decklists available")
            else:
                card_id2card_data = get_card_id_card_data_lookup()
                decklist_data: DecklistData = tournament_standings2decklist_data(tournament_standings, card_id2card_data)
                decklist_data.avg_price_eur = mean(decklist_id2price_eur.values())
                decklist_data.avg_price_usd = mean(decklist_id2price_usd.values())

                card_ids_sorted = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                                         key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
                card_ids_filtered = [card_id for card_id in card_ids_sorted if
                                     card_id != leader_id and decklist_data.card_id2occurrence_proportion[card_id] >= 0.02]
                st.write(f"Number of decks: {len(tournament_standings)}")
                st.write(
                    f"Average Price: {'%.2f' % decklist_data.avg_price_eur}€ | ${'%.2f' % decklist_data.avg_price_usd}")
                col1, col2, col3 = st.columns([0.4, 0.5, 0.1])
                col1.image(f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_{OPTcgLanguage.EN.upper()}.webp")

                with col2:
                    display_list_view(decklist_data, card_ids_filtered)

                selected_matching_decklist = get_best_matching_decklist(tournament_standings, decklist_data)
                if selected_matching_decklist:
                    st.subheader("Average Decklist")
                    player_id = st.selectbox("Select Players Decklist", [ts.player_id for ts in tournament_standings],
                                             index=None)
                    if player_id:
                        selected_matching_decklist = \
                        [ts.decklist for ts in tournament_standings if ts.player_id == player_id][0]
                    selected_matching_decklist.pop(leader_id)
                    display_decklist(selected_matching_decklist, is_mobile())
                else:
                    st.warning("No decklists available. Please change the 'Start Date'")


