import time

import pandas as pd
import streamlit as st
from statistics import mean

from pydantic import BaseModel, field_validator
from streamlit_elements import elements, mui, dashboard, html as element_html

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderElo, LeaderExtended
from op_tcg.backend.models.cards import OPTcgLanguage, CardCurrency
from op_tcg.backend.models.tournaments import TournamentStanding, TournamentStandingExtended, TournamentDecklist
from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select, display_sortby_select, \
    LeaderCardMovementSortBy
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_tournament_standing_data, get_leader_extended, \
    get_tournament_decklist_data, get_card_id_card_data_lookup
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid, lname_and_lid_to_lid, \
    get_lid2ldata_dict_cached
from op_tcg.frontend.utils.material_ui_fns import display_table, value2color_table_cell, create_image_cell
from op_tcg.frontend.utils.query_params import get_default_leader_name, add_query_param
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data, DecklistData
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.styles import css_rule_to_dict, read_style_sheet


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

def get_avg_price(tournament_standings: list[TournamentStanding] | list[TournamentDecklist], currency: CardCurrency) -> float:
    card_id2card_data = get_card_id_card_data_lookup()
    return mean([get_decklist_price(ts.decklist, card_id2card_data, currency=currency) for ts in tournament_standings])

@timeit
def main_leader_card_movement():
    st.header("Leader Card Movement")
    header_stylings = css_rule_to_dict(read_style_sheet("table", ".sticky-header"))
    header_stylings["font-size"] = "20px;"
    table_cell_styles = css_rule_to_dict(read_style_sheet("table", ".colored-table-cell"))

    with st.sidebar:
        selected_meta_format: MetaFormat = display_meta_select(multiselect=False)[0]
        previous_meta_format: MetaFormat = MetaFormat.to_list()[MetaFormat.to_list().index(selected_meta_format) - 1]

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
        dict.fromkeys([l.id for l in leader_extended_data if all(mf in lid2meta_formats[l.id] for mf in [previous_meta_format, selected_meta_format])]))
    if len(available_leader_ids) == 0:
        st.warning("No leader data available for the selected meta")
        return None
    available_leader_names = [lid_to_name_and_lid(lid) for lid in available_leader_ids]
    default_leader_name = get_default_leader_name(available_leader_ids)

    with st.sidebar:
        selected_leader_name: str = display_leader_select(available_leader_names=available_leader_names, key="select_lid",
                                                          multiselect=False, default=default_leader_name,
                                                          on_change=lambda: add_query_param("lid", lname_and_lid_to_lid(st.session_state.get("select_lid", "")))
                                                          )
        sort_by: LeaderCardMovementSortBy = display_sortby_select(LeaderCardMovementSortBy)
        threshold: int = st.slider("Min Occurrence Change (in %)", min_value=2, max_value=100, value=10)

    if selected_leader_name:
        leader_id: str = lname_and_lid_to_lid(selected_leader_name)
        tournament_decklist_data_previous_meta = get_tournament_decklist_data(meta_formats=[previous_meta_format], leader_ids=[leader_id])
        tournament_decklist_data_selected_meta = get_tournament_decklist_data(meta_formats=[selected_meta_format], leader_ids=[leader_id])

        if len(tournament_decklist_data_selected_meta) == 0 or len(tournament_decklist_data_previous_meta) == 0:
            st.warning("No decklists available")
        else:
            card_id2card_data = get_card_id_card_data_lookup()
            decklist_data_previous_meta: DecklistData = tournament_standings2decklist_data(
                tournament_decklist_data_previous_meta, card_id2card_data)
            decklist_data_selected_meta: DecklistData = tournament_standings2decklist_data(
                tournament_decklist_data_selected_meta, card_id2card_data)
            card_movement:  dict[str, CardMovement] = get_card_movement(decklist_data_previous_meta, decklist_data_selected_meta)
            avg_price_eur_previous_meta = get_avg_price(tournament_decklist_data_previous_meta, currency=CardCurrency.EURO)
            avg_price_eur_selected_meta = get_avg_price(tournament_decklist_data_selected_meta, currency=CardCurrency.EURO)
            avg_price_usd_previous_meta = get_avg_price(tournament_decklist_data_previous_meta, currency=CardCurrency.US_DOLLAR)
            avg_price_usd_selected_meta = get_avg_price(tournament_decklist_data_selected_meta, currency=CardCurrency.US_DOLLAR)

            col1, col2, col3, col4, col5 = st.columns([5,1,4,1,5])
            with col1:
                st.write(f"Number of decks ({previous_meta_format}): {len(tournament_decklist_data_previous_meta)}")
                st.write(f"Average price: {'%.2f' % avg_price_eur_previous_meta}€ | ${'%.2f' % avg_price_usd_previous_meta}")
                # st.subheader("Decklist Loser")
                # for key in sorted(card_movement, key=lambda lid: card_movement[lid].occurrence_proportion_change):
                #     if card_movement[key].occurrence_proportion_change < -(threshold/100):
                #         st.image(decklist_data_previous_meta.card_id2card_data[key].image_url)
                #         st.write(f"Occurrence {int(card_movement[key].occurrence_proportion_before*100)}% -> {int(card_movement[key].occurrence_proportion_after*100)}%")
            with col3:
                st.subheader("Decklist Leader")
                st.image(decklist_data_selected_meta.card_id2card_data[leader_id].image_url)
            with col5:
                st.write(f"Number of decks ({selected_meta_format}): {len(tournament_decklist_data_selected_meta)}")
                st.write(f"Average price: {'%.2f' % avg_price_eur_selected_meta}€ | ${'%.2f' % avg_price_usd_selected_meta}")
                # st.subheader("Decklist Winner")
                # for key in sorted(card_movement, key=lambda lid: card_movement[lid].occurrence_proportion_change, reverse=True):
                #     if card_movement[key].occurrence_proportion_change > (threshold/100):
                #         st.image(decklist_data_selected_meta.card_id2card_data[key].image_url)
                #         st.write(f"Occurrence {int(card_movement[key].occurrence_proportion_before*100)}% -> {int(card_movement[key].occurrence_proportion_after*100)}%")


            with elements("dashboard"):
                # Layout for every element in the dashboard
                layout = [
                    # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
                    dashboard.Item("card_movement_table_item", 0, 0, 12, 6, isResizable=False, isDraggable=False),
                ]

                df_data = {previous_meta_format: [], selected_meta_format: [],
                           "Change": []}
                card_movement_sorted = sorted(card_movement, key=lambda lid: card_movement[lid].occurrence_proportion_change, reverse=sort_by == LeaderCardMovementSortBy.CARD_MOVEMENT_WINNER)
                index_cells = []

                def _to_percentage_string(value: float) -> str:
                    return f"{int(100 * value)}%"
                for card_id in card_movement_sorted:
                    movement = card_movement[card_id]
                    change = movement.occurrence_proportion_change
                    if change < -(threshold / 100) or change > (threshold/100):
                        index_cells.append(create_image_cell(card_id2card_data[card_id].image_url,
                                                          text=f"{card_id}",
                                                          overlay_color=card_id2card_data[card_id].to_hex_color(),
                                                          horizontal=True))
                        df_data[previous_meta_format].append(mui.TableCell(_to_percentage_string(movement.occurrence_proportion_before)))
                        df_data[selected_meta_format].append(mui.TableCell(_to_percentage_string(movement.occurrence_proportion_after)))
                        df_data["Change"].append(value2color_table_cell(change, max_value=1, min_value=-1, cell_input=_to_percentage_string(change), styles=table_cell_styles))

                header_cells = [mui.TableCell(children="Card", sx={"width": "200px", **header_stylings})] + [
                    mui.TableCell(col, sx=header_stylings) for col in
                    list(df_data.keys())]
                df_display = pd.DataFrame(df_data)

                with dashboard.Grid(layout):
                    display_table(df_display,
                                  index_cells=[index_cells],
                                  header_cells=header_cells,
                                  title=None,
                                  key="card_movement_table_item")