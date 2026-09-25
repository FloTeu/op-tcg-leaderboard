import pytest
from bs4 import BeautifulSoup

from op_tcg.backend.crawling.spiders.limitless_prices import LimitlessPricesSpider
from op_tcg.backend.etl.extract import (
    extract_card_prices,
    extract_marketplace_urls,
    parse_price,
)
from op_tcg.backend.models.cards import CardCurrency, OPTcgLanguage, OPTcgMarketplace

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


# --- aa_version attribution ---
#
# limitless renders the prints table once per print ("card-page-main" block). In every copy
# the row of the print *that block shows* is marked `current` and carries no href, while the
# other rows link to their print - aa_version 0 without a `v` param, alt arts with `?v=N`.

def _print_row(href: str | None, usd: str, eur: str, is_current: bool = False) -> str:
    link = f'<a href="{href}">' if href else "<a>"
    tr = '<tr class="current">' if is_current else "<tr>"
    return (
        f"{tr}"
        f"<td>{link}Memorial Collection</a></td>"
        f'<td><a class="card-price usd" href="https://tcgplayer.example/{usd}">{usd}</a></td>'
        f'<td><a class="card-price eur" href="https://cardmarket.example/{eur}">{eur}</a></td>'
        f"</tr>"
    )


def _prints_table_soup(*rows: str) -> BeautifulSoup:
    return BeautifulSoup(
        '<div class="card-page-main"><table class="card-prints-versions">'
        "<tr><th>Print</th><th>USD</th><th>EUR</th></tr>" + "".join(rows) + "</table></div>",
        "html.parser",
    )


def test_extract_card_prices_uses_links_not_row_order():
    """Rows are attributed by their own '?v=' link, even when listed out of order."""
    soup = _prints_table_soup(
        _print_row(None, "$24.29", "10.96€", is_current=True),      # v=0, current block
        _print_row("/cards/en/EB01-006?v=3", "$1,400.00", "134.87€"),
        _print_row("/cards/en/EB01-006?v=1", "$132.98", "60.12€"),
        _print_row("/cards/en/EB01-006?v=2", "$3,250.00", "3,268.64€"),
    )

    prices = extract_card_prices("EB01-006", OPTcgLanguage.EN, soup)
    eur = {p.aa_version: p.price for p in prices if p.currency == CardCurrency.EURO}

    assert eur == pytest.approx({0: 10.96, 3: 134.87, 1: 60.12, 2: 3268.64})


def test_extract_card_prices_attributes_current_row_to_its_own_block():
    """
    In the block of a non-zero print, the link-less 'current' row is that print - NOT v=0.
    v=0 is the row linked without a 'v' query param.
    """
    soup = _prints_table_soup(
        _print_row("/cards/en/EB01-006", "$24.29", "10.96€"),        # v=0: href, no 'v' param
        _print_row("/cards/en/EB01-006?v=1", "$132.98", "60.12€"),
        _print_row(None, "$3,250.00", "3,268.64€", is_current=True),  # v=2: this block's print
        _print_row("/cards/en/EB01-006?v=3", "$1,400.00", "134.87€"),
    )

    prices = extract_card_prices("EB01-006", OPTcgLanguage.EN, soup, current_aa_version=2)
    eur = {p.aa_version: p.price for p in prices if p.currency == CardCurrency.EURO}

    assert eur == pytest.approx({0: 10.96, 1: 60.12, 2: 3268.64, 3: 134.87})


def test_extract_card_prices_raises_when_two_rows_resolve_to_same_version():
    """
    A print maps to exactly one aa_version, so two rows resolving to the same one means the
    table was mis-read (here: the current row's version was not passed in, colliding with v=0).
    Better to fail the card than to attribute a price to the wrong version.
    """
    soup = _prints_table_soup(
        _print_row("/cards/en/EB01-006", "$24.29", "10.96€"),         # -> 0
        _print_row(None, "$3,250.00", "3,268.64€", is_current=True),  # -> current_aa_version
    )

    with pytest.raises(ValueError, match="aa_version 0 resolved more than once"):
        extract_card_prices("EB01-006", OPTcgLanguage.EN, soup, current_aa_version=0)


# Real block for EB04-054 (Bartholomew Kuma) as rendered on the OP16 set page, trimmed to the
# parts the extractors read. The card's original print belongs to EB04 and its v=1 print to
# OP16, so on this page the link-less 'current' row is v=1 - not v=0. Note the browser-inserted
# <tbody>, which must not break row lookup.
EB04_054_OP16_BLOCK_HTML = """
<div class="card-page-main">
<div class="card-profile">
<div class="card-image">
<img class="card shadow resp-w" src="https://limitlesstcg.nyc3.cdn.digitaloceanspaces.com/one-piece/EB04/EB04-054_p1_EN.webp"/>
</div>
<div class="card-details"><div class="card-details-main"><div class="card-text">
<div class="card-text-section">
<p class="card-text-title">
<span class="card-text-name"><a href="/cards/EB04-054?v=1">Bartholomew Kuma</a></span>
<span class="card-text-id">EB04-054</span>
</p>
</div>
</div></div></div>
</div>
<div class="card-prints">
<div class="card-prints-current">
<a href="/cards/op16-the-time-of-battle">
<div class="prints-current-details">
<span class="text-lg">The Time of Battle (OP16)</span>
<span>Special Card</span>
</div>
</a>
</div>
<table class="card-prints-versions">
<tbody><tr>
<th>Print</th><th>USD</th><th>EUR</th>
</tr>
<tr>
<td>
<a href="/cards/EB04-054">
Adventure on Kami's Island
<span class="prints-table-card-number"></span>
</a>
</td>
<td> <a class="card-price usd" href="https://partner.tcgplayer.com/ONEPIECE?u=685325-eb04-054" target="_blank">$0.17</a> </td>
<td> <a class="card-price eur" href="https://www.cardmarket.com/en/OnePiece/Products/Singles/Adventure-on-Kamis-Island/Bartholomew-Kuma-EB04-054" target="_blank">0.13€</a> </td>
</tr>
<tr class="current">
<td>
<a>
The Time of Battle
<span class="prints-table-card-number"></span>
</a>
</td>
<td> <a class="card-price usd" href="https://partner.tcgplayer.com/ONEPIECE?u=695509-bartholomew-kuma-sp" target="_blank">$62.56</a> </td>
<td> <a class="card-price eur" href="https://www.cardmarket.com/en/OnePiece/Products/Singles/OP16/Bartholomew-Kuma-EB04-054" target="_blank">78.89€</a> </td>
</tr>
</tbody></table>
</div></div>
"""


def test_print_introduced_by_a_later_set_keeps_its_own_version():
    """
    A set can introduce a non-zero print of a card first released elsewhere. The block's own
    version comes from its card-text-name link, and the link-less 'current' row belongs to it -
    previously that row was hardcoded to 0, which silently dropped its marketplace urls.
    """
    block = BeautifulSoup(EB04_054_OP16_BLOCK_HTML, "html.parser").find("div", class_="card-page-main")
    own_aa_version = LimitlessPricesSpider._block_aa_version(block)
    assert own_aa_version == 1

    prices = extract_card_prices("EB04-054", OPTcgLanguage.EN, block, current_aa_version=own_aa_version)
    assert {(p.aa_version, p.currency): p.price for p in prices} == pytest.approx({
        (0, CardCurrency.US_DOLLAR): 0.17,   # Adventure on Kami's Island (EB04)
        (0, CardCurrency.EURO): 0.13,
        (1, CardCurrency.US_DOLLAR): 62.56,  # The Time of Battle (OP16)
        (1, CardCurrency.EURO): 78.89,
    })

    marketplace_urls = extract_marketplace_urls(
        block, "EB04-054", OPTcgLanguage.EN, [own_aa_version], current_aa_version=own_aa_version
    )
    assert {(m.aa_version, m.marketplace) for m in marketplace_urls} == {
        (1, OPTcgMarketplace.TCGPLAYER),
        (1, OPTcgMarketplace.CARDMARKET),
    }
    assert all("OP16" in m.url or "695509" in m.url for m in marketplace_urls)


def test_extract_marketplace_urls_attributes_current_row_to_its_own_block():
    soup = _prints_table_soup(
        _print_row("/cards/en/EB01-006", "$24.29", "10.96€"),          # v=0
        _print_row(None, "$3,250.00", "3,268.64€", is_current=True),   # v=2, this block's print
    )

    marketplace_urls = extract_marketplace_urls(
        soup, "EB01-006", OPTcgLanguage.EN, aa_versions=[2], current_aa_version=2
    )

    assert {(m.aa_version, m.marketplace) for m in marketplace_urls} == {
        (2, OPTcgMarketplace.TCGPLAYER),
        (2, OPTcgMarketplace.CARDMARKET),
    }
    # the v=2 row's links, not v=0's
    assert all("3,2" in m.url for m in marketplace_urls)
