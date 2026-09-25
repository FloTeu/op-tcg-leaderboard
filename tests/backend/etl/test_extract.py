import pytest
from bs4 import BeautifulSoup

from op_tcg.backend.etl.extract import extract_card_prices, parse_price
from op_tcg.backend.models.cards import CardCurrency, OPTcgLanguage

# Real card-page-main block for EB01-006 (Tony Tony.Chopper), captured from limitless.
# aa_version 2 ("manga") and aa_version 3's USD cell are both above 1000 and use a
# "," thousands separator, e.g. "$3,250.00" / "3,268.64€".
EB01_006_CARD_PAGE_HTML = """
<div class="card-page-main">
<div class="card-profile">
<div class="card-image">
<img class="card shadow resp-w" data-lightbox="on" data-src="https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/one-piece/EB01/EB01-006_EN.webp" height="838" src="https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/one-piece/EB01/EB01-006_EN.webp" width="600"/>
</div>
<div class="card-details">
<div class="card-details-main">
<div class="card-text">
<div class="card-text-section">
<p class="card-text-title">
<span class="card-text-name"><a href="/cards/en/EB01-006">Tony Tony.Chopper</a></span>
<span class="card-text-id">EB01-006</span>
</p>
<p class="card-text-type">
<span data-tooltip="Category">Character</span>
            &bull; <span data-tooltip="Color">Red</span>
             &bull; 3 Cost
                    </p>
</div>
<p class="card-text-section">
            4000 Power
            &bull; <span data-tooltip="Attribute">Strike</span>
             &bull; +1000 Counter         </p>
<div class="card-text-section">
                    [Blocker] <span class="reminder-text">(After your opponent declares an attack, you may rest this card to make it the new target of the attack.)</span><br/>[DON!! x2] [When Attacking] Give up to 1 of your opponent's Characters &minus;3000 power during this turn.


    </div>
<div class="card-text-section">
<span data-tooltip="Type">Animal/Straw Hat Crew</span>
</div>
<div class="card-text-section card-text-artist">
            Illustrated by
            <a href="/cards/en?q=!artist:kito">
                kito
            </a>
</div>
</div>
<div class="card-legality">
<div class="regulation-mark">
     Block 2</div>
<div class="card-legality-group">
<div class="card-legality-badge">
<div>Standard</div>
<div class="legal">
         legal     </div>
</div> <div class="card-legality-badge">
<div>Extra</div>
<div class="legal">
         legal     </div>
</div></div>
<div class="card-legality-notes">
</div> </div>
</div>
</div>
</div>
<div class="card-prints">
<div class="card-prints-current">
<a href="/cards/en/eb01-memorial-collection">
<div class="prints-current-details">
<span class="text-lg">
                    Memorial Collection
                     (EB01)                 </span>
<span>
                     Super Rare
                                    </span>
</div>
</a>
</div>
<table class="card-prints-versions">
<tr>
<th>Print</th>
<th>USD</th>
<th>EUR</th>
</tr>
<tr class="current">
<td>
<a>
                        Memorial Collection
                        <span class="prints-table-card-number"></span>
</a>
</td>
<td> <a class="card-price usd" href="https://partner.tcgplayer.com/ONEPIECE?u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F544530%2Fone-piece-card-game-extra-booster-memorial-collection-tony-tonychopper" target="_blank">$24.29</a> </td>
<td> <a class="card-price eur" href="https://www.cardmarket.com/en/OnePiece/Products/Singles/Memorial-Collection/Tony-TonyChopper-EB01-006-V1?utm_source=limitlesstcg&amp;utm_medium=text&amp;utm_campaign=card_prices" target="_blank">10.96€</a> </td>
</tr>
<tr>
<td>
<a href="/cards/en/EB01-006?v=1">
                        Memorial Collection
                        <span class="prints-table-card-number">aa</span>
</a>
</td>
<td> <a class="card-price usd" href="https://partner.tcgplayer.com/ONEPIECE?u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F544531%2Fone-piece-card-game-extra-booster-memorial-collection-tony-tonychopper-alternate-art" target="_blank">$132.98</a> </td>
<td> <a class="card-price eur" href="https://www.cardmarket.com/en/OnePiece/Products/Singles/Memorial-Collection/Tony-TonyChopper-EB01-006-V2?utm_source=limitlesstcg&amp;utm_medium=text&amp;utm_campaign=card_prices" target="_blank">60.12€</a> </td>
</tr>
<tr>
<td>
<a href="/cards/en/EB01-006?v=2">
                        Memorial Collection
                        <span class="prints-table-card-number">manga</span>
</a>
</td>
<td> <a class="card-price usd" href="https://partner.tcgplayer.com/ONEPIECE?u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F544532%2Fone-piece-card-game-extra-booster-memorial-collection-tony-tonychopper-alternate-art-manga" target="_blank">$3,250.00</a> </td>
<td> <a class="card-price eur" href="https://www.cardmarket.com/en/OnePiece/Products/Singles/Memorial-Collection/Tony-TonyChopper-EB01-006-V3?utm_source=limitlesstcg&amp;utm_medium=text&amp;utm_campaign=card_prices" target="_blank">3,268.64€</a> </td>
</tr>
<tr>
<td>
<a href="/cards/en/EB01-006?v=3">
                        Prize Cards
                        <span class="prints-table-card-number">aa</span>
</a>
</td>
<td> <a class="card-price usd" href="https://partner.tcgplayer.com/ONEPIECE?u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F590986%2Fone-piece-card-game-one-piece-promotion-cards-tony-tonychopper-treasure-cup-2024" target="_blank">$1,400.00</a> </td>
<td> <a class="card-price eur" href="https://www.cardmarket.com/en/OnePiece/Products/Singles/Special-Tournaments-Promos/Tony-TonyChopper-EB01-006?utm_source=limitlesstcg&amp;utm_medium=text&amp;utm_campaign=card_prices" target="_blank">134.87€</a> </td>
</tr>
</table>
</div> </div>
"""


def _make_price_cell(html: str):
    return BeautifulSoup(f"<td>{html}</td>", "html.parser").find("td")


# --- parse_price ---

@pytest.mark.parametrize("column,cell_html,expected_currency,expected_price", [
    ("USD", '<a class="card-price usd" href="#">$24.29</a>', CardCurrency.US_DOLLAR, 24.29),
    ("EUR", '<a class="card-price eur" href="#">10.96€</a>', CardCurrency.EURO, 10.96),
    # values >= 1000 use a "," thousands separator on limitless
    ("USD", '<a class="card-price usd" href="#">$3,250.00</a>', CardCurrency.US_DOLLAR, 3250.00),
    ("EUR", '<a class="card-price eur" href="#">3,268.64€</a>', CardCurrency.EURO, 3268.64),
    ("USD", '<a class="card-price usd" href="#">$1,400.00</a>', CardCurrency.US_DOLLAR, 1400.00),
])
def test_parse_price_handles_thousands_separator(column, cell_html, expected_currency, expected_price):
    currency, price = parse_price(column, _make_price_cell(cell_html))
    assert currency == expected_currency
    assert price == pytest.approx(expected_price)


# --- extract_card_prices ---

def test_extract_card_prices_handles_values_above_1000():
    soup = BeautifulSoup(EB01_006_CARD_PAGE_HTML, "html.parser")
    prices = extract_card_prices("EB01-006", OPTcgLanguage.EN, soup)

    price_by_version_currency = {(p.aa_version, p.currency): p.price for p in prices}

    expected = {
        (0, CardCurrency.US_DOLLAR): 24.29,
        (0, CardCurrency.EURO): 10.96,
        (1, CardCurrency.US_DOLLAR): 132.98,
        (1, CardCurrency.EURO): 60.12,
        (2, CardCurrency.US_DOLLAR): 3250.00,
        (2, CardCurrency.EURO): 3268.64,
        (3, CardCurrency.US_DOLLAR): 1400.00,
        (3, CardCurrency.EURO): 134.87,
    }

    assert price_by_version_currency.keys() == expected.keys()
    for key, expected_price in expected.items():
        assert price_by_version_currency[key] == pytest.approx(expected_price)
