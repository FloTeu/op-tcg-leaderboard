from functools import partial

import pandas as pd
import streamlit as st
from statistics import mean

from cssutils.css import CSSStyleSheet
from pydantic import BaseModel, field_validator
from streamlit.components import v1 as components
from streamlit_elements import elements, mui, dashboard, html as element_html

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderElo, LeaderExtended
from op_tcg.backend.models.cards import OPTcgLanguage, CardCurrency, LatestCardPrice
from op_tcg.backend.models.tournaments import TournamentStanding, TournamentStandingExtended, TournamentDecklist
from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select, display_sortby_select, \
    LeaderCardMovementSortBy
from op_tcg.frontend.utils.chart import create_line_chart
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_tournament_standing_data, get_leader_extended, \
    get_tournament_decklist_data, get_card_id_card_data_lookup
from op_tcg.frontend.utils.js import execute_js_file
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid, \
    get_lid2ldata_dict_cached
from op_tcg.frontend.utils.material_ui_fns import display_table, value2color_table_cell, create_image_cell
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data, DecklistData
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.styles import css_rule_to_dict, read_style_sheet
from op_tcg.frontend.views.card import get_card_attribute_html
from op_tcg.frontend.views.modal import display_card_details_dialog


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


def card_id2line_chart(card_id: str, meta_format2decklist_data: dict[MetaFormat, DecklistData],
                       max_width: str | None = None, enable_x_axis: bool = False):
    def _get_deck_occurrence_proportion(dd: DecklistData) -> float | None:
        if card_id in dd.card_id2occurrence_proportion:
            return int(dd.card_id2occurrence_proportion[card_id] * 100)
        else:
            return None

    data_dict = {mf: _get_deck_occurrence_proportion(dd) for mf, dd in meta_format2decklist_data.items()}
    # fill up missing data
    unequal_none = False
    for mf, data in data_dict.items():
        if data is not None:
            unequal_none = True
        elif unequal_none:
            # if meta already exists unequal None, next metas should have at least 0 value
            data_dict[mf] = 0.0

    line_plot = create_line_chart(data_dict, "Occ. (in %)", enable_y_axis=False, enable_x_top_axis=enable_x_axis,
                                  use_custom_component=False, fill_up_missing_meta_format=False)
    return mui.TableCell(mui.Box(line_plot, sx={"height": 120, "max-width": max_width}),
                         sx={"padding": "0px", "max-width": max_width, "width": max_width})


def get_avg_price(tournament_standings: list[TournamentStanding] | list[TournamentDecklist],
                  currency: CardCurrency) -> float:
    card_id2card_data = get_card_id_card_data_lookup()
    return mean([get_decklist_price(ts.decklist, card_id2card_data, currency=currency) for ts in tournament_standings])


def get_previous_meta_format(meta_format: MetaFormat) -> MetaFormat:
    return MetaFormat.to_list()[MetaFormat.to_list().index(meta_format) - 1]


def get_leader_extended_data(leader_id: str) -> LeaderExtended | None:
    """Get extended data about the leader inkl. aa image url"""
    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    leader_extended = None
    leader_extended_filtered = [le for le in leader_extended_data if le.id == leader_id and le.only_official == True]
    if len(leader_extended_filtered) > 0:
        leader_extended = leader_extended_filtered[0]
    return leader_extended


def _display_meta_card(tournament_decklist_data: list[TournamentDecklist],
                       meta_format: MetaFormat,
                       avg_price_eur: float,
                       avg_price_usd: float,
                       css_stylings: CSSStyleSheet):
    card_attributes_html = f"""
        {get_card_attribute_html(f"Number of decks ({meta_format})", len(tournament_decklist_data))}
        {get_card_attribute_html(f"Average price", '%.2f' % avg_price_eur + "€ | $" + '%.2f' % avg_price_usd)}
    """

    meta_html = f"""
        <div class="card">
            <h1 class="card-title">Meta: {meta_format}</h1>
            {card_attributes_html}
        </div>
        """

    components.html(f"""
        <style> 
        {css_stylings.cssText.decode()}
        </style>
        <body>
        {meta_html}
        </body>""", height=200, scrolling=False)

@timeit
def main_leader_card_movement():
    st.header("Leader Card Movement")

    with st.sidebar:
        selected_meta_format: MetaFormat = display_meta_select(multiselect=False)[0]
        previous_meta_format: MetaFormat = get_previous_meta_format(selected_meta_format)

    leader_extended_data: list[LeaderExtended] = get_leader_extended()
    lid2meta_formats = {}
    for led in leader_extended_data:
        if led.id not in lid2meta_formats:
            lid2meta_formats[led.id] = [led.meta_format]
        else:
            lid2meta_formats[led.id].append(led.meta_format)

    # first element is leader with best d_score
    leader_extended_data = list(
        filter(lambda x: x.meta_format in [selected_meta_format],
               leader_extended_data))
    leader_extended_data.sort(key=lambda x: x.d_score, reverse=True)
    available_leader_ids = list(
        dict.fromkeys([l.id for l in leader_extended_data if
                       all(mf in lid2meta_formats[l.id] for mf in [previous_meta_format, selected_meta_format])]))
    if len(available_leader_ids) == 0:
        st.warning("No leader data available for the selected meta")
        return None
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids)

    with st.sidebar:
        selected_leader_name: str = display_leader_select(available_leader_names=available_leader_names,
                                                          key="select_lid",
                                                          multiselect=False, default=default_leader_name,
                                                          on_change=lambda: add_query_param("lid", lname_and_lid_to_lid(
                                                              st.session_state.get("select_lid", "")))
                                                          )

    st.text(
        f"This page shows the card movement for leader {selected_leader_name} from meta {previous_meta_format} to meta {selected_meta_format}")

    if selected_leader_name:
        leader_id: str = lname_and_lid_to_lid(selected_leader_name)
        leader_data: None | LeaderExtended = get_leader_extended_data(leader_id)

        tournament_decklist_data = get_tournament_decklist_data(meta_formats=MetaFormat.to_list(),
                                                                leader_ids=[leader_id])
        tournament_decklist_data_previous_meta = [dd for dd in tournament_decklist_data if
                                                  dd.meta_format == previous_meta_format]
        tournament_decklist_data_selected_meta = [dd for dd in tournament_decklist_data if
                                                  dd.meta_format == selected_meta_format]

        if len(tournament_decklist_data_selected_meta) == 0 or len(tournament_decklist_data_previous_meta) == 0:
            st.warning("No decklists available")
        else:
            card_id2card_data = get_card_id_card_data_lookup()
            avg_price_eur_previous_meta = get_avg_price(tournament_decklist_data_previous_meta,
                                                        currency=CardCurrency.EURO)
            avg_price_eur_selected_meta = get_avg_price(tournament_decklist_data_selected_meta,
                                                        currency=CardCurrency.EURO)
            avg_price_usd_previous_meta = get_avg_price(tournament_decklist_data_previous_meta,
                                                        currency=CardCurrency.US_DOLLAR)
            avg_price_usd_selected_meta = get_avg_price(tournament_decklist_data_selected_meta,
                                                        currency=CardCurrency.US_DOLLAR)

            col1, col2, col3 = st.columns([0.25, 0.05, 0.5])
            with col1:
                st.subheader("Decklist Leader")
                if leader_data:
                    st.image(leader_data.aa_image_url)
                else:
                    st.image(card_id2card_data[leader_id].image_url)
            with col3:
                st.subheader("")

                card_attr_css = read_style_sheet("card_attributes")
                _display_meta_card(tournament_decklist_data_selected_meta, selected_meta_format,
                                   avg_price_eur_selected_meta, avg_price_usd_selected_meta, card_attr_css)
                _display_meta_card(tournament_decklist_data_previous_meta, previous_meta_format,
                                   avg_price_eur_previous_meta, avg_price_usd_previous_meta, card_attr_css)

            display_card_movement_table(card_id2card_data, tournament_decklist_data,
                                        selected_meta_format)

            # Reload page if iframe does not load leader table correctly
            execute_js_file("missing_iframe_table", display_none=False)


@st.fragment
def display_card_movement_table(card_id2card_data, tournament_decklists: list[TournamentDecklist],
                                selected_meta_format):
    n_meta_formats_to_display = 5

    # frontend interactables
    cols = st.columns([0.2, 0.8])
    with cols[0]:
        sort_by: LeaderCardMovementSortBy = display_sortby_select(LeaderCardMovementSortBy)
    with cols[1]:
        threshold: int = st.slider("Min Occurrence Change (in %)", min_value=0, max_value=100, value=10)

    header_stylings = css_rule_to_dict(read_style_sheet("table", ".sticky-header"))
    header_stylings["font-size"] = "20px;"
    table_cell_styles = css_rule_to_dict(read_style_sheet("table", ".colored-table-cell"))

    all_meta_formats_until_selected = MetaFormat.to_list(until_meta_format=selected_meta_format)
    previous_meta_format: MetaFormat = get_previous_meta_format(selected_meta_format)
    meta_format2decklist_data: dict[MetaFormat, DecklistData] = {}
    n_meta_formats = len(all_meta_formats_until_selected)
    for meta_format in all_meta_formats_until_selected[max(0, n_meta_formats - n_meta_formats_to_display):]:
        tournament_decklists_meta = [dd for dd in tournament_decklists if dd.meta_format == meta_format]
        meta_format2decklist_data[meta_format] = tournament_standings2decklist_data(
            tournament_decklists_meta, card_id2card_data)

    card_movement: dict[str, CardMovement] = get_card_movement(meta_format2decklist_data[previous_meta_format],
                                                               meta_format2decklist_data[selected_meta_format])

    with elements("dashboard"):
        # Layout for every element in the dashboard
        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item("card_movement_table_item", 0, 0, 12, 6, isResizable=False, isDraggable=False),
        ]

        df_data = {previous_meta_format: [], selected_meta_format: [],
                   "Change": [], "Deck Occurrence": []}
        card_movement_sorted = sorted(card_movement,
                                      key=lambda lid: card_movement[lid].occurrence_proportion_change,
                                      reverse=sort_by == LeaderCardMovementSortBy.CARD_MOVEMENT_WINNER)

        def _filter_card_movement(card_id: str):
            change = card_movement[card_id].occurrence_proportion_change
            return change < -(threshold / 100) or change > (threshold / 100)

        def _open_dialog(card_id: str, carousel_card_ids: list[str] | None):
            # reset index offset for modal/dialog
            st.session_state["card_details_index_offset"] = 0
            display_card_details_dialog(card_id, carousel_card_ids)

        card_movement_sorted = list(filter(lambda x: _filter_card_movement(x), card_movement_sorted))
        index_cells = []
        max_width = "220px"

        def _to_percentage_string(value: float) -> str:
            return f"{int(100 * value)}%"

        for i, card_id in enumerate(card_movement_sorted):
            movement = card_movement[card_id]
            change = movement.occurrence_proportion_change
            index_cells.append(create_image_cell(card_id2card_data.get(card_id, LatestCardPrice.from_default()).image_url,
                                                 text=f"{card_id}",
                                                 overlay_color=card_id2card_data.get(card_id, LatestCardPrice.from_default()).to_hex_color(),
                                                 horizontal=True,
                                                 on_click=partial(
                                                     _open_dialog, card_id=card_id,
                                                     carousel_card_ids=card_movement_sorted)
                                                 ))
            df_data[previous_meta_format].append(
                mui.TableCell(_to_percentage_string(movement.occurrence_proportion_before)))
            df_data[selected_meta_format].append(
                mui.TableCell(_to_percentage_string(movement.occurrence_proportion_after)))
            df_data["Change"].append(value2color_table_cell(change, max_value=1, min_value=-1,
                                                            cell_input=_to_percentage_string(change),
                                                            styles=table_cell_styles))
            # df_data["Deck Occurrence"].append(
            #     mui.TableCell(_to_percentage_string(movement.occurrence_proportion_before)))
            df_data["Deck Occurrence"].append(
                card_id2line_chart(card_id, meta_format2decklist_data, max_width=max_width, enable_x_axis=i==0))

        header_cells = [mui.TableCell(children="Card", sx={"width": "200px", **header_stylings})] + [
            mui.TableCell(col, sx={"max-width": max_width, **header_stylings}
            if col == "Deck Occurrence" else header_stylings) for col in list(df_data.keys())]
        df_display = pd.DataFrame(df_data)

        with dashboard.Grid(layout):
            display_table(df_display,
                          index_cells=[index_cells],
                          header_cells=header_cells,
                          title=None,
                          key="card_movement_table_item")

    t = 0
