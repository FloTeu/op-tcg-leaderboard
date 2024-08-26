import streamlit as st
from statistics import mean

from pydantic import BaseModel, field_validator
from streamlit_elements import elements, mui, dashboard, html as element_html

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderElo
from op_tcg.backend.models.cards import OPTcgLanguage, CardCurrency
from op_tcg.backend.models.tournaments import TournamentStanding, TournamentStandingExtended
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_tournament_standing_data
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid, \
    get_lid2ldata_dict_cached
from op_tcg.frontend.utils.query_params import add_query_param, get_default_leader_name
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data, DecklistData, \
    get_card_id_card_data_lookup, get_decklist_price


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


class CardMovement(BaseModel):
    occurrence_proportion_before: float
    occurrence_proportion_after: float
    occurrence_proportion_change: float

    @field_validator("occurrence_proportion_before", "occurrence_proportion_after", "occurrence_proportion_change")
    @classmethod
    def round_floats(cls, value):
        return float("%.2f" % value)



def get_card_movement(decklist_data_past: DecklistData, decklist_data_current: DecklistData) -> dict[str, CardMovement]:
    card_movement: dict[str, CardMovement] = {}

    def add_card_movement(card_id):
        if card_id not in card_movement:
            occurrence_proportion_before = decklist_data_past.card_id2occurrence_proportion.get(card_id, 0.0)
            occurrence_proportion_after = decklist_data_current.card_id2occurrence_proportion.get(card_id, 0.0)
            card_movement[card_id] = CardMovement(
                occurrence_proportion_before=occurrence_proportion_before,
                occurrence_proportion_after=occurrence_proportion_after,
                occurrence_proportion_change=occurrence_proportion_after - occurrence_proportion_before,
            )

    for card_id in decklist_data_current.card_id2occurrence_proportion.keys():
        add_card_movement(card_id)
    for card_id in decklist_data_past.card_id2occurrence_proportion.keys():
        add_card_movement(card_id)
    return card_movement

def get_avg_price(tournament_standings: list[TournamentStanding], currency: CardCurrency) -> float:
    card_id2card_data = get_card_id_card_data_lookup()
    return mean([get_decklist_price(ts.decklist, card_id2card_data, currency=currency) for ts in tournament_standings])

def main_leader_decklist_movement():
    st.header("Leader Decklist Movement")

    with st.sidebar:
        selected_meta_format: MetaFormat = display_meta_select(multiselect=False)[0]
        previous_meta_format: MetaFormat = MetaFormat.to_list()[MetaFormat.to_list().index(selected_meta_format) - 1]

    selected_leader_elo_data: list[LeaderElo] = get_leader_elo_data(meta_formats=[selected_meta_format])
    leader_id2leader_data = get_lid2ldata_dict_cached()
    available_leader_ids = list(dict.fromkeys([l.leader_id for l in selected_leader_elo_data if l.leader_id in leader_id2leader_data and leader_id2leader_data[l.leader_id].meta_format != selected_meta_format]))
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids)
    with st.sidebar:
        selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_names, key="select_lid",
                                                          multiselect=False, default=default_leader_name,
                                                          on_change=add_query_param, kwargs={"lid": "select_lid"})
        threshold: int = st.slider("Min Occurrence Change (in %)", min_value=5, max_value=100, value=40)

    if selected_leader_name:
        leader_id: str = lname_and_lid_to_lid(selected_leader_name)
        # TODO: Try using get_tournament_decklist_data instead
        tournament_standings_previous_meta: list[TournamentStandingExtended] = get_tournament_standing_data(
            meta_formats=[previous_meta_format], leader_id=leader_id)
        tournament_standings_selected_meta: list[TournamentStandingExtended] = get_tournament_standing_data(
            meta_formats=[selected_meta_format], leader_id=leader_id)

        if len(tournament_standings_selected_meta) == 0 or len(tournament_standings_previous_meta) == 0:
            st.warning("No decklists available")
        else:
            card_id2card_data = get_card_id_card_data_lookup()
            decklist_data_previous_meta: DecklistData = tournament_standings2decklist_data(
                tournament_standings_previous_meta, card_id2card_data)
            decklist_data_selected_meta: DecklistData = tournament_standings2decklist_data(
                tournament_standings_selected_meta, card_id2card_data)
            card_movement = get_card_movement(decklist_data_previous_meta, decklist_data_selected_meta)
            avg_price_eur_previous_meta = get_avg_price(tournament_standings_previous_meta, currency=CardCurrency.EURO)
            avg_price_eur_selected_meta = get_avg_price(tournament_standings_selected_meta, currency=CardCurrency.EURO)
            avg_price_usd_previous_meta = get_avg_price(tournament_standings_previous_meta, currency=CardCurrency.US_DOLLAR)
            avg_price_usd_selected_meta = get_avg_price(tournament_standings_selected_meta, currency=CardCurrency.US_DOLLAR)


            col1, col2, col3, col4, col5 = st.columns([5,1,4,1,5])
            with col1:
                st.write(f"Number of decks ({previous_meta_format}): {len(tournament_standings_previous_meta)}")
                st.write(f"Average price: {'%.2f' % avg_price_eur_previous_meta}€ | ${'%.2f' % avg_price_usd_previous_meta}")
                st.subheader("Decklist Loser")
                for key in sorted(card_movement, key=lambda lid: card_movement[lid].occurrence_proportion_change):
                    if card_movement[key].occurrence_proportion_change < -(threshold/100):
                        st.image(decklist_data_previous_meta.card_id2card_data[key].image_url)
                        st.write(f"Occurrence {int(card_movement[key].occurrence_proportion_before*100)}% -> {int(card_movement[key].occurrence_proportion_after*100)}%")
            with col3:
                st.subheader("Decklist Leader")
                st.image(decklist_data_selected_meta.card_id2card_data[leader_id].image_url)
            with col5:
                st.write(f"Number of decks ({selected_meta_format}): {len(tournament_standings_selected_meta)}")
                st.write(f"Average price: {'%.2f' % avg_price_eur_selected_meta}€ | ${'%.2f' % avg_price_usd_selected_meta}")
                st.subheader("Decklist Winner")
                for key in sorted(card_movement, key=lambda lid: card_movement[lid].occurrence_proportion_change, reverse=True):
                    if card_movement[key].occurrence_proportion_change > (threshold/100):
                        st.image(decklist_data_selected_meta.card_id2card_data[key].image_url)
                        st.write(f"Occurrence {int(card_movement[key].occurrence_proportion_before*100)}% -> {int(card_movement[key].occurrence_proportion_after*100)}%")
