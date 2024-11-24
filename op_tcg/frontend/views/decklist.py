import streamlit as st
from pathlib import Path

from streamlit.components import v1 as components
from streamlit_elements import elements, dashboard, mui, html as element_html

from op_tcg.backend.models.cards import LatestCardPrice, OPTcgLanguage
from op_tcg.frontend import styles, scripts, html
from op_tcg.frontend.utils.decklist import DecklistData


def display_list_view(decklist_data: DecklistData, card_ids: list[str]):
    lis = ""

    for i, card_id in enumerate(card_ids):
        card_data: LatestCardPrice | None = decklist_data.card_id2card_data.get(card_id, None)
        op_set = card_id.split("-")[0]
        occurrence_percantage = decklist_data.card_id2occurrence_proportion[card_id]
        card_headline_str = card_data.name if card_data else card_id
        card_headline_str = card_headline_str[0:20] + " [...]" if len(card_headline_str) > 25 else card_headline_str
        card_headline_html = f'<h2 class="item-title">{card_headline_str}</h2>'
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
    
    <div class="item-fact-circle" style="background: rgba(123, 237, 159, {occurrence_percantage})">
      {int(occurrence_percantage * 100)}%
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
    n_cols = 1 if is_mobile else 3
    n_st_cols = st.columns([1 / n_cols for i in range(n_cols)])

    for i, (card_id, card_occurrence) in enumerate(decklist.items()):
        with n_st_cols[i % n_cols]:
            op_set = card_id.split("-")[0]
            image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
            st.image(image_url)
            st.markdown(f"### **x{card_occurrence}**")
    # add scrollbar
    css = '''
        <style>
            div[data-testid="stExpanderDetails"] {
                overflow: scroll;
                height: 500px;
            }
        </style>
    '''
    st.markdown(css, unsafe_allow_html=True)


def display_decklist_old(decklist: dict[str, int], is_mobile: bool):
    with elements("dashboard"):
        # First, build a default layout for every element you want to include in your dashboard
        num_cols = 3
        layout = [
            # Parameters: element_identifier, x_pos, y_pos, width, height, [item properties...]
            dashboard.Item(f"item_{card_id}", ((i * 2) % (num_cols * 2)), 0, 2, 3, isResizable=False,
                           isDraggable=not is_mobile, preventCollision=True)
            for i, (card_id, _) in enumerate(decklist.items())
        ]

        # Next, create a dashboard layout using the 'with' syntax. It takes the layout
        # as first parameter, plus additional properties you can find in the GitHub links below.

        with dashboard.Grid(layout):
            for card_id, count in decklist.items():
                op_set = card_id.split("-")[0]
                image_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
                # mui.Box(component="img", src=image_url, alt=f"image_{card_id}", sx={"display": "flex"}, key=f"item_{card_id}")
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
