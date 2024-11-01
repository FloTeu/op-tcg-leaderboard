from pathlib import Path

from streamlit.components import v1 as components

from op_tcg.backend.models.cards import LatestCardPrice, OPTcgLanguage
from op_tcg.frontend import styles, scripts, html
from op_tcg.frontend.utils.decklist import DecklistData


def display_list_view(decklist_data: DecklistData, card_ids: list[str]):
    lis = ""

    for i, card_id in enumerate(card_ids):
        card_data: LatestCardPrice | None = decklist_data.card_id2card_data.get(card_id, None)
        op_set = card_id.split("-")[0]
        occurence_percantage = decklist_data.card_id2occurrence_proportion[card_id]
        card_headline_html = f'<h2 class="item-title">{card_data.name if card_data else card_id}</h2>'
        img_src = card_data.image_url if card_data else f'https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp'
        price_html = f'<li>Price: {card_data.latest_eur_price}€ | ${card_data.latest_usd_price}</li>' if card_data else ''
        lis += f"""
<li class="list-item">
    <div class="item-image" data-index="{i}" onclick="openModal(this)">
      <img src="{img_src}" alt="Item Image">
    </div>
    <div class="item-details">
      {card_headline_html}
      <ul class="item-facts">
        <li>Card ID: {card_id}</li>
        <li>Occurrence: {int(decklist_data.card_id2occurrence_proportion[card_id] * 100)}%</li>
        <li>Average Count in Deck: {decklist_data.card_id2avg_count_card[card_id]} ({round(decklist_data.card_id2avg_count_card[card_id])})</li>
        {price_html}
        <!-- Add more facts as needed -->
      </ul>
    </div>
    
    <div class="item-fact-circle" style="background: rgba(123, 237, 159, {occurence_percantage})">
      {int(occurence_percantage * 100)}%
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
