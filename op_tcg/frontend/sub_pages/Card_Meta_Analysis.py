import pandas as pd
import streamlit as st
from pydantic import Field, BaseModel
from streamlit_elements import elements, mui, dashboard, html as element_html

from op_tcg.backend.models.cards import OPTcgColor, OPTcgLanguage, LatestCardPrice, OPTcgCardCatagory
from op_tcg.backend.models.tournaments import TournamentStandingExtended
from op_tcg.backend.utils.leader_fns import df_win_rate_data2lid_dicts
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data, DecklistData, \
    get_card_id_card_data_lookup
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_win_rate, get_tournament_standing_data, \
    get_card_data
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select, display_only_official_toggle, \
    display_leader_color_multiselect, display_card_color_multiselect
from op_tcg.frontend.utils.js import is_mobile
from op_tcg.frontend.utils.leader_data import lid2ldata_fn, lids_to_name_and_lids, lname_and_lid_to_lid

from streamlit_theme import st_theme

ST_THEME = st_theme(key=str(__file__)) or {"base": "dark"}


class ExtendedCardData(BaseModel):
    card_id: str
    occurrence_in_decklists: float = Field(
        description="Value between 0 and 1 indicating occurrence of card in decklist with same color")
    image_url: str | None


@st.cache_data(ttl=60 * 60 * 24)  # 1 day
def get_extended_card_data(card_id: str, decklists: list[dict[str, int]],
                           image_url: str | None = None) -> ExtendedCardData:
    """
    card_id: Id of card, e.g. OP01-001
    tournament_standings: list of tournament standings with decklist/leader in same color as card_id
    """
    count_in_decklist = 0
    for decklist in decklists:
        if card_id in decklist:
            count_in_decklist += 1

    return ExtendedCardData(
        card_id=card_id,
        occurrence_in_decklists=0.0 if len(decklists) == 0 else count_in_decklist / len(decklists),
        image_url=image_url
    )


def display_cards(cards_data: list[ExtendedCardData], is_mobile: bool):
    with elements("dashboard"):
        # First, build a default layout for every element you want to include in your dashboard
        num_cols = 3
        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item(f"item_{extended_card_data.card_id}", ((i * 2) % (num_cols * 2)), 0, 2, 3, isResizable=False,
                           isDraggable=not is_mobile, preventCollision=True)
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
        selected_meta_formats: list[MetaFormat] = display_meta_select()
        selected_card_colors: list[OPTcgColor] | None = display_card_color_multiselect(default=[OPTcgColor.RED])
    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
    if len(selected_card_colors) == 0:
        st.warning("Please select at least one color")
    else:
        card_data_lookup: dict[str, LatestCardPrice] = get_card_id_card_data_lookup(aa_version=0)
        card_data_lookup = {cid: cd for cid, cd in card_data_lookup.items() if (
                any(color in selected_card_colors for color in cd.colors)
        )}
        tournament_standings: list[TournamentStandingExtended] = get_tournament_standing_data(
            meta_formats=selected_meta_formats)
        if len(tournament_standings) == 0:
            st.warning("No decklists available")
        elif len(card_data_lookup) == 0:
            st.warning("No cards available")
        else:
            extended_card_data_list: list[ExtendedCardData] = []
            for cid, cdata in card_data_lookup.items():
                if cdata.card_category == OPTcgCardCatagory.LEADER:
                    continue

                # keep only tournament standings with decklist and color equal to card
                tournament_standings_filtered = [ts for ts in tournament_standings if (
                        ts.decklist and
                        ts.leader_id in card_data_lookup and
                        any(ccolor in card_data_lookup[ts.leader_id].colors for ccolor in cdata.colors)
                )]
                extended_card_data_list.append(get_extended_card_data(cid, [ts.decklist for ts in tournament_standings_filtered],
                                                                      image_url=cdata.image_url))

            extended_card_data_list.sort(key=lambda x: x.occurrence_in_decklists, reverse=True)

            display_cards(extended_card_data_list[0:30], is_mobile())
