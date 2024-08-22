from datetime import datetime, date, timedelta

import streamlit as st
from statistics import mean

from op_tcg.backend.models.input import MetaFormat, meta_format2release_datetime
from op_tcg.backend.models.leader import LeaderElo
from op_tcg.backend.models.cards import OPTcgLanguage, LatestCardPrice, CardCurrency
from op_tcg.backend.models.tournaments import TournamentStanding, TournamentStandingExtended
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data, DecklistData, \
    get_card_id_card_data_lookup
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_tournament_standing_data
from op_tcg.frontend.utils.js import is_mobile
from op_tcg.frontend.utils.query_params import add_query_param, get_default_leader_name
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid
from streamlit_elements import elements, mui, dashboard, html as element_html

from op_tcg.frontend.views.decklist import display_list_view


def get_decklist_price(decklist: dict[str, int], card_id2card_data: dict[str, LatestCardPrice],
                       currency: CardCurrency = CardCurrency.EURO) -> float:
    deck_price = 0.0
    for card_id, count in decklist.items():
        card_data = card_id2card_data.get(card_id, None)
        if currency == CardCurrency.EURO:
            deck_price += card_data.latest_eur_price * count if card_data else 0.0
        elif currency == CardCurrency.US_DOLLAR:
            deck_price += card_data.latest_usd_price * count if card_data else 0.0
        else:
            raise NotImplementedError
    return deck_price


def get_best_matching_decklist(tournament_standings: list[TournamentStandingExtended], decklist_data: DecklistData) -> \
dict[str, int]:
    decklists: list[dict[str, int]] = [ts.decklist for ts in tournament_standings]
    card_ids_sorted: list[str] = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                                        key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
    should_have_card_ids_in_decklist: set[str] = set()
    card_count: float = 0.0
    for card_id in card_ids_sorted:
        if card_count < 51:  # 50 + leader
            should_have_card_ids_in_decklist.add(card_id)
            card_count += decklist_data.card_id2avg_count_card[card_id]
    best_matching_decklist: dict[str, int] = {}
    best_overlap = 0
    for decklist in decklists:
        card_in_decklist = set(decklist.keys())
        current_overlap = len(card_in_decklist.intersection(should_have_card_ids_in_decklist))
        if best_overlap < current_overlap:
            best_matching_decklist = decklist
            best_overlap = current_overlap

    return best_matching_decklist


def display_decklist(decklist: dict[str, int], is_mobile: bool):
    with elements("dashboard"):
        # First, build a default layout for every element you want to include in your dashboard
        num_cols = 3
        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item(f"item_{card_id}", ((i * 2) % (num_cols * 2)), 0, 2, 3, isResizable=False,
                           isDraggable=not is_mobile, preventCollision=True)
            for i, (card_id, _) in enumerate(decklist.items())
        ]

        # Next, create a dashboard layout using the 'with' syntax. It takes the layout
        # as first parameter, plus additional properties you can find in the GitHub links below.

        with dashboard.Grid(layout):
            for card_id, count in decklist.items():
                op_set = card_id.split("-")[0]
                image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
                # mui.Box(component="img", src=image_url, alt=f"image_{card_id}", sx={"display": "flex"}, key=f"item_{card_id}")
                mui.Container(
                    children=[
                        # Image at the top
                        element_html.Img(src=image_url, style={"width": "100%", "height": "auto"}),
                        # Text block below the image
                        mui.Typography(
                            variant="h5",
                            component="h2",
                            children=f"x {count}",
                            gutterBottom=True
                        )], key=f"item_{card_id}"
                )

def main_leader_detail_analysis_decklists():
    st.header("Leader Decklist")

    with st.sidebar:
        selected_meta_formats: list[MetaFormat] = display_meta_select(multiselect=True)

    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
    else:

        selected_leader_elo_data: list[LeaderElo] = get_leader_elo_data(meta_formats=selected_meta_formats)
        available_leader_ids = list(dict.fromkeys([l.leader_id for l in selected_leader_elo_data]))
        available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
        default_leader_name = get_default_leader_name(available_leader_ids)
        with st.sidebar:
            selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_names, key="select_lid",
                                                              multiselect=False, default=default_leader_name, on_change=add_query_param, kwargs={"lid": "select_lid"})
            oldest_release_data: date = datetime.now().date()
            oldest_release_datetime: datetime = datetime.now()
            for meta_format in selected_meta_formats:
                release_date = meta_format2release_datetime(meta_format)
                if release_date.date() < oldest_release_data:
                    oldest_release_data = release_date.date()
                    oldest_release_datetime = release_date

        if selected_leader_name:
            leader_id: str = lname_and_lid_to_lid(selected_leader_name)
            tournament_standings: list[TournamentStandingExtended] = get_tournament_standing_data(
                meta_formats=selected_meta_formats, leader_id=leader_id)
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
                decklist_data: DecklistData = tournament_standings2decklist_data(tournament_standings)
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
                col1.image(
                    f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_{OPTcgLanguage.EN.upper()}.webp",
                    width=400,  # Manually Adjust the width of the image as per requirement
                    )
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


