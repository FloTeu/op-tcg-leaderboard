import pandas as pd
import streamlit as st
from pydantic import Field, BaseModel
from streamlit_elements import elements, mui, dashboard, html as element_html

from op_tcg.backend.models.cards import OPTcgColor, OPTcgLanguage, LatestCardPrice, OPTcgCardCatagory, OPTcgAbility, \
    CardPopularity, CardCurrency
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.decklist import get_card_id_card_data_lookup
from op_tcg.frontend.utils.extract import get_card_popularity_data
from op_tcg.frontend.sidebar import display_meta_select, display_card_color_multiselect, display_card_ability_multiselect
from op_tcg.frontend.utils.js import is_mobile

from streamlit_theme import st_theme

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}


class ExtendedCardData(BaseModel):
    card_id: str
    occurrence_in_decklists: float = Field(
        description="Value between 0 and 1 indicating occurrence of card in decklist with same color")
    image_url: str | None




def display_cards(cards_data: list[ExtendedCardData], is_mobile: bool):
    with elements("dashboard"):
        # First, build a default layout for every element you want to include in your dashboard
        num_cols = 3
        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item(f"item_{extended_card_data.card_id}", ((i * 2) % (num_cols * 2)), 0, 2, 3, isResizable=False,
                           isDraggable=False, preventCollision=True)
            for i, extended_card_data in enumerate(cards_data)
        ]

        # Next, create a dashboard layout using the 'with' syntax. It takes the layout
        # as first parameter, plus additional properties you can find in the GitHub links below.

        with dashboard.Grid(layout):
            for extended_card_data in cards_data:
                op_set = extended_card_data.card_id.split("-")[0]
                image_url = extended_card_data.image_url
                if image_url is None:
                    image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{extended_card_data.card_id}_{OPTcgLanguage.EN.upper()}.webp"
                # mui.Box(component="img", src=image_url, alt=f"image_{card_id}", sx={"display": "flex"}, key=f"item_{card_id}")
                mui.Container(
                    children=[
                        # Image at the top
                        element_html.Img(src=image_url, style={"width": "100%", "height": "auto"}),
                        # Text block below the image
                        mui.Typography(
                            variant="h5",
                            component="h2",
                            children=f"{int(extended_card_data.occurrence_in_decklists * 100)}%",
                            gutterBottom=True
                        )], key=f"item_{extended_card_data.card_id}"
                )


def main_card_meta_analysis():
    st.header("Card Meta Analysis")

    with st.sidebar:
        selected_meta_format: MetaFormat = display_meta_select(multiselect=False)[0]
        selected_card_colors: list[OPTcgColor] | None = display_card_color_multiselect(default=[OPTcgColor.RED])
        selected_card_counter: int | None = st.selectbox("Counter", [0, 1000, 2000], index=None)
        selected_card_category: OPTcgCardCatagory | None = st.selectbox("Card Type", OPTcgCardCatagory.to_list(), index=None)
        filter_currency = st.selectbox("Currency", [CardCurrency.EURO, CardCurrency.US_DOLLAR])
        selected_card_cost_min, selected_card_cost_max = st.slider("Card Cost Range", 0, 10, (0,10))
        selected_min_price, selected_max_price = st.slider("Decklist Price Range", 0, 80, (0,80))
        selected_card_abilities: list[OPTcgAbility] | None = display_card_ability_multiselect()
        card_ability_text: str = st.text_input("Card Ability Text")
        filter_operator: str = st.selectbox("Filter Operator", ["OR", "AND"])
    if len(selected_card_colors) == 0:
        st.warning("Please select at least one color")
    else:
        not_selected_counter = False
        if selected_card_counter is None:
            not_selected_counter = True
        elif selected_card_counter == 0:
            selected_card_counter = None
        card_data_lookup: dict[str, LatestCardPrice] = get_card_id_card_data_lookup(aa_version=0)
        card_data_lookup = {cid: cd for cid, cd in card_data_lookup.items() if (
                any(color in selected_card_colors for color in cd.colors) and
                (True if not_selected_counter else selected_card_counter == cd.counter) and
                (True if not selected_card_category else selected_card_category == cd.card_category) and
                (True if cd.cost is None else selected_card_cost_min <= cd.cost <= selected_card_cost_max) and
                (selected_min_price <= (cd.latest_eur_price if filter_currency == CardCurrency.EURO else cd.latest_usd_price) <= selected_max_price)
        )}
        card_popularity: list[CardPopularity] = get_card_popularity_data()
        card_popularity_dict = {cp.card_id: cp.popularity for cp in card_popularity if (
            cp.card_id in card_data_lookup and
            selected_meta_format == cp.meta_format and
            any(cp.color == card_color for card_color in card_data_lookup[cp.card_id].colors)
        )}
        if len(card_data_lookup) == 0:
            st.warning("No cards available")
        else:
            extended_card_data_list: list[ExtendedCardData] = []
            for cid, cdata in card_data_lookup.items():
                if not selected_card_category and cdata.card_category == OPTcgCardCatagory.LEADER:
                    continue
                if selected_card_abilities is not None:
                    card_has_any_ability = any([ability in cdata.ability for ability in selected_card_abilities]) or (card_ability_text and card_ability_text.lower() in cdata.ability.lower())
                    card_has_all_ability = all([ability in cdata.ability for ability in selected_card_abilities]) and (True if not card_ability_text else card_ability_text.lower() in cdata.ability.lower())
                    if filter_operator == "OR" and not card_has_any_ability:
                        continue
                    elif filter_operator == "AND" and not card_has_all_ability:
                        continue
                if cid not in card_popularity_dict:
                    continue
                extended_card = ExtendedCardData(
                    card_id=cid,
                    occurrence_in_decklists=card_popularity_dict[cid],
                    image_url=cdata.image_url
                )
                extended_card_data_list.append(extended_card)

            extended_card_data_list.sort(key=lambda x: x.occurrence_in_decklists, reverse=True)

            display_cards(extended_card_data_list[0:30], is_mobile())
