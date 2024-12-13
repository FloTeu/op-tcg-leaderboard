import streamlit as st
import logging
from pydantic import Field, BaseModel

from op_tcg.backend.models.cards import OPTcgColor, OPTcgCardCatagory, OPTcgAbility, \
    CardPopularity, CardCurrency, OPTcgAttribute, ExtendedCardData
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.extract import get_card_popularity_data, get_card_id_card_data_lookup
from op_tcg.frontend.sidebar import display_meta_select, display_card_color_multiselect, \
    display_card_ability_multiselect, display_card_fraction_multiselect, display_release_meta_select, \
    display_card_attribute_multiselect
from op_tcg.frontend.utils.js import is_mobile, execute_js_file

from streamlit_theme import st_theme

from op_tcg.frontend.utils.styles import GREEN_RGB, read_style_sheet
from op_tcg.frontend.views.modal import display_card_details_dialog

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}


class DisplayCardData(BaseModel):
    card_id: str
    card_name: str
    occurrence_in_decklists: float = Field(
        description="Value between 0 and 1 indicating occurrence of card in decklist with same color")
    image_url: str | None

def display_cards(cards_data: list[DisplayCardData], is_mobile: bool):
    css_class_card = read_style_sheet("grid_view", selector=".card")
    css_class_progress_container = read_style_sheet("progress_bar", selector=".progress-container")
    css_class_progress_bar = read_style_sheet("progress_bar", selector=".progress-bar")
    css_class_progress_bar.style.backgroundColor = f"rgba({GREEN_RGB[0]},{GREEN_RGB[1]},{GREEN_RGB[2]}, 50)"
    n_cols = 1 if is_mobile else 3

    n_st_cols = st.columns([1 / n_cols for i in range(n_cols)])

    card_html = f"""
    <html><style>
        {css_class_card.cssText}
        {css_class_progress_container.cssText}
        {css_class_progress_bar.cssText}
    </style></html>"""
    st.markdown(card_html, unsafe_allow_html=True)

    carousel_card_ids = [cd.card_id for cd in cards_data]
    for i, card_data in enumerate(cards_data):
        with n_st_cols[i % n_cols]:
            width = f"{int(max(card_data.occurrence_in_decklists, 0.1) * 100)}%"
            card_name = card_data.card_name
            # if len(card_name) > 18:
            #     card_name = card_name[:18] + " [...]"
            header_hashtags = "###"
            if len(card_name) > 14:
                header_hashtags = "####"
            if len(card_name) > 18:
                header_hashtags = "#####"
            if len(card_name) > 20:
                header_hashtags = "######"

            _, col1, col3, _ = st.columns([0.05, 0.8, 0.1, 0.15])
            # col1, col3 = st.columns([1,1])
            col1.markdown(f"""{header_hashtags} {card_name}""")
            with col3:
                display_dialog_button(card_data.card_id, carousel_card_ids=carousel_card_ids)
            card_html = f"""
            <html>
            <div class="card">
                <div><img src="{card_data.image_url}" /></div>
                <div class="progress-container">
                    <div class="progress-bar" style="width: {width};">{int(card_data.occurrence_in_decklists * 100)}%
                    </div>
                </div>                
            </div>
            </html>
            """
            st.markdown(card_html, unsafe_allow_html=True)


    execute_js_file("st_columns_prevent_mobile_break_button")

def display_dialog_button(card_id: str, carousel_card_ids: list[str] = None):
    if st.button(":bar_chart:", key=f"card_modal_button_{card_id}"):
        logging.warning(f"Click Open Card Detail Modal {card_id}")
        # reset index offset
        st.session_state["card_details_index_offset"] = 0
        display_card_details_dialog(card_id=card_id, carousel_card_ids=carousel_card_ids)


def main_card_meta_analysis():
    st.header("Card Popularity")
    st.write(
        "A list of cards ordered by popularity. A popularity of 100% stands for 100% occurrence in tournament decks of the same card color.")

    search_term = st.text_input("Search term (e.g. Name, type, release meta etc.)", help="Helpful shortcut: Split search term by ';' in order to combine search conditions with AND logic")
    with st.sidebar:
        selected_meta_format: MetaFormat = display_meta_select(multiselect=False, label="Meta")[0]
        selected_release_meta_formats: list[MetaFormat] = display_release_meta_select(multiselect=True,
                                                                                      label="Release Meta",
                                                                                      default=None)
        selected_card_colors: list[OPTcgColor] | None = display_card_color_multiselect(default=OPTcgColor.to_list())
        selected_card_attributes: list[OPTcgAttribute] | None = display_card_attribute_multiselect(default=None)
        selected_card_counter: int | None = st.selectbox("Counter", [0, 1000, 2000], index=None)
        selected_card_category: OPTcgCardCatagory | None = st.selectbox("Card Type", OPTcgCardCatagory.to_list(),
                                                                        index=None)
        selected_types: list[str] = display_card_fraction_multiselect()
        filter_currency = st.selectbox("Currency", [CardCurrency.EURO, CardCurrency.US_DOLLAR])
        price_min, price_max = 0, 80
        selected_min_price, selected_max_price = st.slider("Card Price Range", price_min, price_max,
                                                           (price_min, price_max))
        selected_card_cost_min, selected_card_cost_max = st.slider("Card Cost Range", 0, 10, (0, 10))
        selected_card_power_min, selected_card_power_max = st.slider("Card Power Range (in k)", 0, 15, (0, 15))
        st.markdown("""---""")
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
        card_data_lookup: dict[str, ExtendedCardData] = get_card_id_card_data_lookup(aa_version=0)
        price_filter_activated = selected_min_price != price_min or selected_max_price != price_max
        if price_filter_activated:
            # filter cards without price information
            card_data_lookup = {cid: cd for cid, cd in card_data_lookup.items() if
                                cd.latest_eur_price and cd.latest_usd_price}
        card_data_lookup = {cid: cd for cid, cd in card_data_lookup.items() if (
                (True if not search_term else all(term.strip().lower() in cd.get_searchable_string().lower() for term in search_term.split(";"))) and
                any(color in selected_card_colors for color in cd.colors) and
                (True if not selected_card_attributes else any(attribute in selected_card_attributes for attribute in cd.attributes)) and
                (True if not_selected_counter else selected_card_counter == cd.counter) and
                (True if len(selected_release_meta_formats) == 0 else any(
                    meta == cd.meta_format for meta in selected_release_meta_formats)) and
                (True if not selected_card_category else selected_card_category == cd.card_category) and
                (True if not selected_types else any(type in selected_types for type in cd.types)) and
                (True if cd.cost is None else selected_card_cost_min <= cd.cost <= selected_card_cost_max) and
                (True if cd.power is None else selected_card_power_min <= cd.power <= selected_card_power_max) and
                (True if not price_filter_activated else (selected_min_price <= (
                    cd.latest_eur_price if filter_currency == CardCurrency.EURO else cd.latest_usd_price) <= selected_max_price))
        )}
        card_popularity_list: list[CardPopularity] = get_card_popularity_data()
        card_popularity_dict = {cp.card_id: cp.popularity for cp in card_popularity_list if (
                cp.card_id in card_data_lookup and
                selected_meta_format == cp.meta_format and
                any(cp.color == card_color for card_color in card_data_lookup[cp.card_id].colors)
        )}
        meta_format_list = MetaFormat.to_list()
        meta_format_list_selected_index = meta_format_list.index(selected_meta_format)
        for card_popularity in card_popularity_list:
            if card_popularity.card_id not in card_popularity_dict and card_popularity.card_id in card_data_lookup and \
                    card_data_lookup[card_popularity.card_id].meta_format:
                # if card is older than selected meta we, include it in card_popularity_dict with popularity 0
                if meta_format_list.index(
                        card_data_lookup[card_popularity.card_id].meta_format) < meta_format_list_selected_index:
                    card_popularity_dict[card_popularity.card_id] = 0.0

        if len(card_data_lookup) == 0:
            st.warning("No cards available")
        else:
            extended_card_data_list: list[DisplayCardData] = []
            for cid, cdata in card_data_lookup.items():
                if not selected_card_category and cdata.card_category == OPTcgCardCatagory.LEADER:
                    continue
                if selected_card_abilities is not None or card_ability_text:
                    if selected_card_abilities is None:
                        selected_card_abilities = []
                    card_has_any_ability = any([ability in cdata.ability for ability in selected_card_abilities]) or (
                                card_ability_text and card_ability_text.lower() in cdata.ability.lower())
                    card_has_all_ability = all([ability in cdata.ability for ability in selected_card_abilities]) and (
                        True if not card_ability_text else card_ability_text.lower() in cdata.ability.lower())
                    if filter_operator == "OR" and not card_has_any_ability:
                        continue
                    elif filter_operator == "AND" and not card_has_all_ability:
                        continue
                if cid not in card_popularity_dict:
                    # if popularity is not available, we expect 0
                    card_popularity_dict[cid] = 0.0
                extended_card = DisplayCardData(
                    card_id=cid,
                    card_name=cdata.name,
                    occurrence_in_decklists=card_popularity_dict[cid],
                    image_url=cdata.image_url
                )
                extended_card_data_list.append(extended_card)

            extended_card_data_list.sort(key=lambda x: x.occurrence_in_decklists, reverse=True)

            display_cards(extended_card_data_list[0:30], is_mobile=is_mobile())

    # change height dynamically based on content
    execute_js_file("iframe_fix_height", display_none=True)