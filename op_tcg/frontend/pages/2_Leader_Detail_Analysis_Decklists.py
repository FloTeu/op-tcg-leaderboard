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
from op_tcg.frontend.utils.leader_data import lid2ldata
import streamlit.components.v1 as components

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
            col1, col2, col3 = st.columns([0.4, 0.5, 0.1])
            col1.image(f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_{OPTcgLanguage.EN.upper()}.webp",
                width=400,  # Manually Adjust the width of the image as per requirement
            )
            with col2:
                display_list_view(decklist_data, card_ids_filtered)


if __name__ == "__main__":
    main()