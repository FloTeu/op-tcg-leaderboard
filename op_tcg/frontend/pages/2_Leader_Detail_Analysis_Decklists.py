import streamlit as st
from pydantic import BaseModel

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import LeaderElo, OPTcgLanguage
from op_tcg.backend.models.tournaments import TournamentStanding
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


def tournament_standings2decklist_data(tournament_standings: list[TournamentStanding]) -> DecklistData:
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

def get_modal_style() -> str:
    return """
    /* Styles for the modal */
      .modal {
        display: none;
        position: fixed;
        z-index: 1000;
        left: 0;
        top: 0;
        width: 100%;
        height: 100%;
        overflow: auto;
        background-color: rgba(0, 0, 0, 0.7);
      }

      .modal-content {
        position: relative;
        background-color: #fefefe;
        margin: 10% auto;
        padding: 20px;
        border: 1px solid #888;
        width: 80%;
        max-width: 700px;
      }

      .modal-close {
        color: #aaa;
        float: right;
        font-size: 28px;
        font-weight: bold;
      }

      .modal-close:hover,
      .modal-close:focus {
        color: black;
        text-decoration: none;
        cursor: pointer;
      }

      .modal-image {
        width: 50%;
        height: auto;
      }
    """

def get_modal_body() -> str:
    return """
    <!-- The Modal -->
    <div id="myModal" class="modal">
      <span class="modal-close" onclick="closeModal()">&times;</span>
      <img class="modal-image" id="img01">
    </div>
    """

def get_modal_script() -> str:
    return """
    // Get the modal
var modal = document.getElementById("myModal");

// Get the image and insert it inside the modal
function openModal(imgElement) {
  var modalImg = document.getElementById("img01");
  modal.style.display = "block";
  modalImg.src = imgElement.querySelector('img').src;
}

// Get the <span> element that closes the modal
function closeModal() {
  modal.style.display = "none";
}

// When the user clicks anywhere outside of the modal, close it
window.onclick = function(event) {
  if (event.target === modal) {
    closeModal();
  }
}"""


def display_list_view(decklist_data: DecklistData, card_ids: list[str]):
    lis = ""

    for card_id in card_ids:
        op_set = card_id.split("-")[0]
        lis += f"""
<li class="list-item">
    <div class="item-image" onclick="openModal(this)">
      <img src="https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp" alt="Item Image">
    </div>
    <div class="item-details">
      <h2 class="item-title">{card_id}</h2>
      <ul class="item-facts">
        <li>Card ID: {card_id}</li>
        <li>Occurrence Proportion: {int(decklist_data.card_id2occurrence_proportion[card_id]*100)}%</li>
        <li>Average Count in Deck: {decklist_data.card_id2avg_count_card[card_id]}</li>
        <!-- Add more facts as needed -->
      </ul>
    </div>
  </li>
"""

    style = """
    
  .list-view {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .list-item {
    display: flex;
    align-items: center;
    border-bottom: 1px solid #ccc;
    padding: 10px;
  }

  .list-item:last-child {
    border-bottom: none;
  }

  .item-image {
    width: 100px;
    height: 100px;
    margin-right: 20px;
    border-radius: 50%;
    overflow: hidden;
  }

  .item-image img {
    width: 100%;
    height: auto;
  }

  .item-details {
    flex-grow: 1;
  }

  .item-title {
    font-size: 1.2em;
    margin: 0 0 5px;
  }

  .item-facts {
    margin: 0;
    padding: 0;
    list-style: none;
  }

  .item-facts li {
    margin-bottom: 5px;
    font-size: 0.9em;
  }
  """ + get_modal_style()

    components.html(f"""
<style> {style} </style>"

<ul class="list-view">
  {lis}
</ul>

{get_modal_body()}

<script>
{get_modal_script()}
</script>
  """,
    height=600, scrolling=True)



    components.html("""

        """)


def main():

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
            selected_leader_names: list[str] = display_leader_select(available_leader_ids=available_leader_ids,
                                                                     multiselect=False)
        if selected_leader_names:
            leader_id: list[str] = [ln.split("(")[1].strip(")") for ln in selected_leader_names][0]
            tournament_standings: list[TournamentStanding] = get_tournament_standing_data(meta_formats=selected_meta_formats, leader_id=leader_id)
            decklist_data: DecklistData = tournament_standings2decklist_data(tournament_standings)
            card_ids_sorted = sorted(decklist_data.card_id2occurrence_proportion.keys(), key=lambda d: decklist_data.card_id2occurrences[d], reverse=True)
            card_ids_sorted = [card_id for card_id in card_ids_sorted if card_id != leader_id]
            st.image(f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{leader_id.split('-')[0]}/{leader_id}_{OPTcgLanguage.EN.upper()}.webp",
                width=400,  # Manually Adjust the width of the image as per requirement
            )
            display_list_view(decklist_data, card_ids_sorted[0:20])
            #add_modal_script()



if __name__ == "__main__":
    main()