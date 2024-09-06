import streamlit as st
from pydantic import Field, BaseModel

from op_tcg.backend.models.cards import OPTcgColor, OPTcgLanguage, LatestCardPrice, OPTcgCardCatagory, OPTcgAbility, \
    CardPopularity, CardCurrency, OPTcgAttribute, ExtendedCardData
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.tournaments import TournamentDecklist
from op_tcg.frontend.utils.chart import create_card_leader_occurrence_stream_chart
from op_tcg.frontend.utils.decklist import get_card_id_card_data_lookup
from op_tcg.frontend.utils.extract import get_card_popularity_data, get_tournament_decklist_data
from op_tcg.frontend.sidebar import display_meta_select, display_card_color_multiselect, \
    display_card_ability_multiselect, display_card_fraction_multiselect, display_release_meta_select, \
    display_card_attribute_multiselect
from op_tcg.frontend.utils.js import is_mobile

from streamlit_theme import st_theme

from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid
from op_tcg.frontend.utils.styles import GREEN_RGB, read_style_sheet, css_rule_to_dict

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


    for i, card_data in enumerate(cards_data):
        with n_st_cols[i % n_cols]:
            width = f"{int(max(card_data.occurrence_in_decklists, 0.1) * 100)}%"
            card_name = card_data.card_name
            # if len(card_name) > 18:
            #     card_name = card_name[:18] + " [...]"
            header_hashtags = "###"
            if len(card_name) > 15:
                header_hashtags = "####"
            if len(card_name) > 18:
                header_hashtags = "#####"
            if len(card_name) > 20:
                header_hashtags = "######"

            _, col1, col3, _ = st.columns([0.05, 0.8, 0.1, 0.15])
            # col1, col3 = st.columns([1,1])
            col1.markdown(f"""{header_hashtags} {card_name}""")
            with col3:
                display_dialog_button(card_data.card_id)
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


def display_dialog_button(card_id: str):
    if st.button(":bar_chart:", key=f"card_modal_button_{card_id}"):
        display_card_details_dialog(card_id=card_id)



@st.dialog("Card Detail", width="large")
def display_card_details_dialog(card_id: str):
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


    with st.spinner():
        cid2card_data = get_card_id_card_data_lookup(aa_version=0)
        card_data = cid2card_data[card_id]
        chart_data, chart_data_meta_formats = get_stream_leader_occurrence_data(cid2card_data, card_id)

        # filter top n most occurring leaders
        top_n_leaders = 5
        most_occurring_leader_ids = get_most_occurring_leader_ids(chart_data)[:top_n_leaders]
        chart_data = [{lid: occ for lid, occ in cd.items() if lid in most_occurring_leader_ids} for cd in chart_data]

        # display data
        st.header(lid_to_name_and_lid(card_id, leader_name=card_data.name))
        col1, col2 = st.columns([0.5, 1])
        col1.image(card_data.image_url)
        with col2:
            pass
            #st.warning(f"Test {card_id}")

        show_normalized = st.toggle("Show normalized data", True)
        if show_normalized:
            try:
                chart_data = normalize_data(chart_data)
            except Exception as e:
                st.error("Sorry something went wrong with the data normalization")

        create_card_leader_occurrence_stream_chart(chart_data, x_tick_labels=chart_data_meta_formats, title=f"Occurrence in Top {top_n_leaders} Leader Decks")


def get_stream_leader_occurrence_data(cid2card_data: dict[str, DisplayCardData], card_id: str):
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


def main_card_meta_analysis():
    st.header("Card Popularity")
    st.write(
        "A list of cards ordered by popularity. A popularity of 100% stands for 100% occurrence in tournament decks of the same card color.")


    with st.sidebar:
        selected_meta_format: MetaFormat = display_meta_select(multiselect=False, label="Meta")[0]
        selected_release_meta_formats: list[MetaFormat] = display_release_meta_select(multiselect=True,
                                                                                      label="Release Meta",
                                                                                      default=None)
        selected_card_colors: list[OPTcgColor] | None = display_card_color_multiselect(default=OPTcgColor.to_list())
        selected_card_attributes: list[OPTcgAttribute] | None = display_card_attribute_multiselect(default=OPTcgAttribute.to_list())
        selected_card_counter: int | None = st.selectbox("Counter", [0, 1000, 2000], index=None)
        selected_card_category: OPTcgCardCatagory | None = st.selectbox("Card Type", OPTcgCardCatagory.to_list(),
                                                                        index=None)
        selected_types: list[str] = display_card_fraction_multiselect()
        filter_currency = st.selectbox("Currency", [CardCurrency.EURO, CardCurrency.US_DOLLAR])
        price_min, price_max = 0, 80
        selected_min_price, selected_max_price = st.slider("Card Price Range", price_min, price_max,
                                                           (price_min, price_max))
        selected_card_cost_min, selected_card_cost_max = st.slider("Card Cost Range", 0, 10, (0, 10))
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
                any(color in selected_card_colors for color in cd.colors) and
                any(attribute in selected_card_attributes for attribute in cd.attributes) and
                (True if not_selected_counter else selected_card_counter == cd.counter) and
                (True if len(selected_release_meta_formats) == 0 else any(
                    meta == cd.meta_format for meta in selected_release_meta_formats)) and
                (True if not selected_card_category else selected_card_category == cd.card_category) and
                (True if not selected_types else any(type in selected_types for type in cd.types)) and
                (True if cd.cost is None else selected_card_cost_min <= cd.cost <= selected_card_cost_max) and
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
                    continue
                extended_card = DisplayCardData(
                    card_id=cid,
                    card_name=cdata.name,
                    occurrence_in_decklists=card_popularity_dict[cid],
                    image_url=cdata.image_url
                )
                extended_card_data_list.append(extended_card)

            extended_card_data_list.sort(key=lambda x: x.occurrence_in_decklists, reverse=True)

            display_cards(extended_card_data_list[0:30], is_mobile=is_mobile())
