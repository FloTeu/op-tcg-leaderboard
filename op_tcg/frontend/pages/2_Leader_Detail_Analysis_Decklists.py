from datetime import datetime, date

import streamlit as st
from pydantic import BaseModel
from pathlib import Path

from op_tcg.backend.etl.transform import meta_format2release_datetime
from op_tcg.frontend import styles, html, scripts
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderElo, OPTcgLanguage
from op_tcg.backend.models.tournaments import TournamentStanding, TournamentStandingExtended
from op_tcg.frontend.sidebar import display_meta_select, display_leader_select
from op_tcg.frontend.utils.extract import get_match_data, get_leader_elo_data, get_tournament_standing_data
#from op_tcg.frontend.utils.js import is_mobile
from op_tcg.frontend.utils.leader_data import lid2ldata
import streamlit.components.v1 as components
from streamlit_elements import elements, mui, nivo, dashboard, html as element_html

st.set_page_config(layout="wide")


class DecklistData(BaseModel):
    num_decklists: int
    card_id2occurrences: dict[str, int]
    card_id2occurrence_proportion: dict[str, float]
    card_id2total_count: dict[str, int]
    card_id2avg_count_card: dict[str, float]


def tournament_standings2decklist_data(tournament_standings: list[TournamentStandingExtended]) -> DecklistData:
    num_decklists = len(tournament_standings)
    card_id2occurrences: dict[str, int] = {}
    card_id2occurrence_proportion: dict[str, float] = {}
    card_id2total_count: dict[str, int] = {}
    card_id2avg_count_card: dict[str, float] = {}
    for tournament_standing in tournament_standings:
        for card_id, count in tournament_standing.decklist.items():
            if card_id not in card_id2occurrences:
                card_id2occurrences[card_id] = 1
                card_id2total_count[card_id] = count
            else:
                card_id2occurrences[card_id] += 1
                card_id2total_count[card_id] += count

    for card_id, total_count in card_id2total_count.items():
        card_id2avg_count_card[card_id] = float("%.2f" % (total_count / card_id2occurrences[card_id]))
        card_id2occurrence_proportion[card_id] = card_id2occurrences[card_id] / num_decklists

    return DecklistData(num_decklists=num_decklists,
                        card_id2occurrences=card_id2occurrences,
                        card_id2occurrence_proportion=card_id2occurrence_proportion,
                        card_id2total_count=card_id2total_count,
                        card_id2avg_count_card=card_id2avg_count_card)

def get_best_matching_decklist(tournament_standings: list[TournamentStandingExtended], decklist_data: DecklistData) -> dict[str, int]:
    decklists: list[dict[str, int]] = [ts.decklist for ts in tournament_standings]
    card_ids_sorted: list[str] = sorted(decklist_data.card_id2occurrence_proportion.keys(),
                             key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
    should_have_card_ids_in_decklist: set[str] = set()
    card_count: float = 0.0
    for card_id in card_ids_sorted:
        if card_count < 51: # 50 + leader
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



def display_list_view(decklist_data: DecklistData, card_ids: list[str]):
    lis = ""

    for card_id in card_ids:
        op_set = card_id.split("-")[0]
        occurence_percantage = decklist_data.card_id2occurrence_proportion[card_id]
        lis += f"""
<li class="list-item">
    <div class="item-image" onclick="openModal(this)">
      <img src="https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp" alt="Item Image">
    </div>
    <div class="item-details">
      <h2 class="item-title">{card_id}</h2>
      <ul class="item-facts">
        <li>Card ID: {card_id}</li>
        <li>Occurrence: {int(decklist_data.card_id2occurrence_proportion[card_id]*100)}%</li>
        <li>Average Count in Deck: {decklist_data.card_id2avg_count_card[card_id]} ({round(decklist_data.card_id2avg_count_card[card_id])})</li>
        <!-- Add more facts as needed -->
      </ul>
    </div>
    
    <div class="item-fact-circle" style="background: rgba(123, 237, 159, {occurence_percantage})">
      {int(occurence_percantage*100)}%
    </div>
    
  </li>
"""

    with open(Path(styles.__path__[0]) / "list_view.css", "r") as fp:
        list_view_css = fp.read()

    with open(Path(styles.__path__[0]) / "modal.css", "r") as fp:
        modal_css = fp.read()

    with open(Path(scripts.__path__[0]) / "modal.js", "r") as fp:
        modal_js = fp.read()

    with open(Path(html.__path__[0]) / "modal.html", "r") as fp:
        modal_html = fp.read()

    components.html(f"""
<style> 
{list_view_css}
{modal_css} 
</style>
<body>
<ul class="list-view">
  {lis}
</ul>

{modal_html}
</body>

<script>
{modal_js}
</script>
  """,
    height=600, scrolling=True)


def display_decklist(decklist: dict[str, int], is_mobile: bool):

    with elements("dashboard"):
        # First, build a default layout for every element you want to include in your dashboard
        num_cols = 3
        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item(f"item_{card_id}", ((i*2)%(num_cols*2)), 0, 2, 3, isResizable=False, isDraggable=not is_mobile, preventCollision=True)
            for i, (card_id, _) in enumerate(decklist.items())
        ]

        # Next, create a dashboard layout using the 'with' syntax. It takes the layout
        # as first parameter, plus additional properties you can find in the GitHub links below.

        with dashboard.Grid(layout):
            for card_id, count in decklist.items():
                op_set = card_id.split("-")[0]
                image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
                #mui.Box(component="img", src=image_url, alt=f"image_{card_id}", sx={"display": "flex"}, key=f"item_{card_id}")
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

def main():
    st.header("Leader Decklist")

    with st.sidebar:
        selected_meta_formats: list[MetaFormat] = display_meta_select(multiselect=True)

    if len(selected_meta_formats) == 0:
        st.warning("Please select at least one meta format")
    else:

        selected_leader_elo_data: list[LeaderElo] = get_leader_elo_data(meta_formats=selected_meta_formats)
        available_leader_ids = list(dict.fromkeys(
            [
                f"{lid2ldata(l.leader_id).name} ({l.leader_id})"
                for l
                in selected_leader_elo_data]))
        with st.sidebar:
            qp_lid = st.query_params.get('lid', None)
            default = f"{lid2ldata(qp_lid).name} ({qp_lid})" if qp_lid else available_leader_ids[0]
            selected_leader_name: str = display_leader_select(available_leader_ids=available_leader_ids,
                                                                     multiselect=False, default=default)
            oldest_release_data: date = datetime.now().date()
            for meta_format in selected_meta_formats:
                release_date = meta_format2release_datetime(meta_format)
                if release_date.date() < oldest_release_data:
                    oldest_release_data = release_date.date()
            start_date: date = st.date_input("Start Date", oldest_release_data)

        if selected_leader_name:
            leader_id: str = selected_leader_name.split("(")[1].strip(")")
            tournament_standings: list[TournamentStandingExtended] = get_tournament_standing_data(meta_formats=selected_meta_formats, leader_id=leader_id)
            # filter by start date
            tournament_standings = [tstand for tstand in tournament_standings if tstand.tournament_timestamp.date() >= start_date]
            decklist_data: DecklistData = tournament_standings2decklist_data(tournament_standings)
            card_ids_sorted = sorted(decklist_data.card_id2occurrence_proportion.keys(), key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
            card_ids_filtered = [card_id for card_id in card_ids_sorted if card_id != leader_id and decklist_data.card_id2occurrence_proportion[card_id] >= 0.02]
            st.write(f"Number of decks: {len(tournament_standings)}")
            col1, col2, col3 = st.columns([0.4, 0.5, 0.1])
            col1.image(f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_{OPTcgLanguage.EN.upper()}.webp",
                width=400,  # Manually Adjust the width of the image as per requirement
            )
            with col2:
                display_list_view(decklist_data, card_ids_filtered)

            selected_matching_decklist = get_best_matching_decklist(tournament_standings, decklist_data)
            st.subheader("Average Decklist")
            player_id = st.selectbox("Select Players Decklist", [ts.player_id for ts in tournament_standings], index=None)
            if player_id:
                selected_matching_decklist = [ts.decklist for ts in tournament_standings if ts.player_id == player_id][0]
            selected_matching_decklist.pop(leader_id)
            display_decklist(selected_matching_decklist, False)





if __name__ == "__main__":
    main()