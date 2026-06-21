import pytest

from op_tcg.backend.crawling.spiders.cardmarket_sealed import (
    detect_language,
    extract_product_id,
    parse_gallery_page,
    parse_price,
    _strip_price_suffix,
)
from op_tcg.backend.models.cards import OPTcgLanguage
from op_tcg.backend.models.sealed import SealedProductType, SealedPriceType


# --- _strip_price_suffix ---

@pytest.mark.parametrize("text,expected", [
    (
        "OP12-JP Legacy of the Master Booster Box Case (12x Booster Box) (Non-English) From 999,95 €",
        "OP12-JP Legacy of the Master Booster Box Case (12x Booster Box) (Non-English)",
    ),
    (
        "OP01 Romance Dawn Booster Box (English) Trend 92,50 €",
        "OP01 Romance Dawn Booster Box (English)",
    ),
    # Name without price suffix is unchanged
    (
        "OP01 Romance Dawn Booster Box (English)",
        "OP01 Romance Dawn Booster Box (English)",
    ),
    # "From" inside product name (not a price suffix) is preserved
    (
        "Signals from the Future Booster Box",
        "Signals from the Future Booster Box",
    ),
])
def test_strip_price_suffix(text, expected):
    assert _strip_price_suffix(text) == expected


# --- parse_price ---

@pytest.mark.parametrize("text,expected", [
    ("89,99 €", 89.99),
    ("1.299,99 €", 1299.99),
    ("1,299.99 €", 1299.99),
    ("92.50 €", 92.50),
    ("0,00 €", 0.0),
])
def test_parse_price(text, expected):
    assert parse_price(text) == pytest.approx(expected, rel=1e-3)


def test_parse_price_invalid():
    assert parse_price("N/A") is None
    assert parse_price("") is None


# --- detect_language ---

@pytest.mark.parametrize("name,expected", [
    ("OP01 Romance Dawn Booster Box (English)", OPTcgLanguage.EN),
    ("OP01 Romance Dawn Booster Box (Japanese)", OPTcgLanguage.JP),
    ("OP01 Romance Dawn Booster Box (EN)", OPTcgLanguage.EN),
    ("OP01 Romance Dawn Booster Box (JP)", OPTcgLanguage.JP),
    ("OP01 Romance Dawn Booster Box", OPTcgLanguage.EN),  # default
    ("OP05 Awakening of the New Era Booster Display JPN", OPTcgLanguage.JP),
    # JP embedded as country-code prefix after hyphen (no word boundary after P)
    ("OP10-JPRoyal Blood Booster Box (Non-English)", OPTcgLanguage.JP),
    ("OP10-JPRoyal Blood Booster Box", OPTcgLanguage.JP),
    # Non-English should NOT resolve to EN despite containing "English"
    ("Some Product (Non-English)", OPTcgLanguage.JP),
])
def test_detect_language(name, expected):
    assert detect_language(name) == expected


# --- extract_product_id ---

@pytest.mark.parametrize("url,expected", [
    (
        "https://www.cardmarket.com/en/OnePiece/Products/Booster-Boxes/OP01-Romance-Dawn-Booster-Box",
        "op01-romance-dawn-booster-box",
    ),
    (
        "/en/OnePiece/Products/Starter-Decks/ST01-Straw-Hat-Crew",
        "st01-straw-hat-crew",
    ),
    (
        "https://www.cardmarket.com/en/OnePiece/Products/Booster-Boxes/OP01-Romance-Dawn-Booster-Box/",
        "op01-romance-dawn-booster-box",
    ),
])
def test_extract_product_id(url, expected):
    assert extract_product_id(url) == expected


# --- parse_gallery_page ---

_IMG_EN = "https://static.cardmarket.com/img/op01-booster-en.jpg"
_IMG_JP = "https://static.cardmarket.com/img/op02-booster-jp.jpg"
_IMG_OP3 = "https://static.cardmarket.com/img/op03-booster.jpg"

_GALLERY_HTML_DT_DD = f"""
<html><body>
<div class="row">
  <div class="col-6">
    <img src="{_IMG_EN}" alt="OP01 EN" />
    <a href="/en/OnePiece/Products/Booster-Boxes/OP01-Romance-Dawn-Booster-Box"
       title="OP01 Romance Dawn Booster Box (English)">OP01 Romance Dawn Booster Box (English)</a>
    <dl>
      <dt>From</dt><dd>89,99 €</dd>
      <dt>Trend</dt><dd>92,50 €</dd>
    </dl>
  </div>
  <div class="col-6">
    <img src="{_IMG_JP}" alt="OP02 JP" />
    <a href="/en/OnePiece/Products/Booster-Boxes/OP02-Paramount-War-Booster-Box"
       title="OP02 Paramount War Booster Box (Japanese)">OP02 Paramount War Booster Box (Japanese)</a>
    <dl>
      <dt>From</dt><dd>150,00 €</dd>
      <dt>Trend</dt><dd>165,00 €</dd>
    </dl>
  </div>
</div>
</body></html>
"""

_GALLERY_HTML_SPAN = f"""
<html><body>
<div class="col-6 productCol">
  <img src="{_IMG_OP3}" alt="OP03" />
  <a href="/en/OnePiece/Products/Booster-Boxes/OP03-Pillars-Of-Strength-Booster-Box"
     title="OP03 Pillars of Strength Booster Box (English)">OP03 Pillars of Strength Booster Box</a>
  <div class="price-container">
    <span>From: </span><span class="color-primary">74,99 €</span>
    <span>Trend: </span><span class="color-primary">78,00 €</span>
  </div>
</div>
</body></html>
"""


def _prices_by_type(prices: list) -> dict:
    return {p.price_type: p for p in prices}


def test_parse_gallery_page_dt_dd():
    results = parse_gallery_page(_GALLERY_HTML_DT_DD, SealedProductType.BOOSTER_BOX)
    assert len(results) == 2

    product, prices = results[0]
    assert product.id == "op01-romance-dawn-booster-box"
    assert product.language == OPTcgLanguage.EN
    assert product.product_type == SealedProductType.BOOSTER_BOX
    assert product.image_url == _IMG_EN
    by_type = _prices_by_type(prices)
    assert by_type[SealedPriceType.TREND].price == pytest.approx(92.50)
    assert by_type[SealedPriceType.FROM].price == pytest.approx(89.99)

    product2, prices2 = results[1]
    assert product2.language == OPTcgLanguage.JP
    assert product2.image_url == _IMG_JP
    by_type2 = _prices_by_type(prices2)
    assert by_type2[SealedPriceType.TREND].price == pytest.approx(165.00)
    assert by_type2[SealedPriceType.FROM].price == pytest.approx(150.00)


def test_parse_gallery_page_span_prices():
    results = parse_gallery_page(_GALLERY_HTML_SPAN, SealedProductType.BOOSTER_BOX)
    assert len(results) == 1
    product, prices = results[0]
    assert product.id == "op03-pillars-of-strength-booster-box"
    assert product.image_url == _IMG_OP3
    by_type = _prices_by_type(prices)
    assert by_type[SealedPriceType.TREND].price == pytest.approx(78.00)
    assert by_type[SealedPriceType.FROM].price == pytest.approx(74.99)


def test_parse_gallery_page_skips_no_image():
    """Products without an image are skipped (navigation/category links)."""
    html = """
    <html><body>
      <div class="col-6">
        <a href="/en/OnePiece/Products/Booster-Boxes/OP01-Test" title="OP01 Test (English)">OP01 Test</a>
        <dl><dt>Trend</dt><dd>90,00 €</dd></dl>
      </div>
    </body></html>
    """
    results = parse_gallery_page(html, SealedProductType.BOOSTER_BOX)
    assert len(results) == 0


def test_parse_gallery_page_skips_category_links():
    html = """
    <html><body>
      <a href="/en/OnePiece/Products/Booster-Boxes">All Booster Boxes</a>
      <div class="col-6">
        <img src="https://static.cardmarket.com/img/op01.jpg" />
        <a href="/en/OnePiece/Products/Booster-Boxes/OP01-Test" title="OP01 Test (English)">OP01 Test</a>
      </div>
    </body></html>
    """
    results = parse_gallery_page(html, SealedProductType.BOOSTER_BOX)
    assert len(results) == 1
    assert results[0][0].id == "op01-test"


def test_parse_gallery_page_no_duplicates():
    img = "https://static.cardmarket.com/img/op01.jpg"
    html = f"""
    <html><body>
      <div class="col-6">
        <img src="{img}" />
        <a href="/en/OnePiece/Products/Booster-Boxes/OP01-Test" title="OP01 Test (English)">OP01 Test</a>
      </div>
      <div class="col-6">
        <img src="{img}" />
        <a href="/en/OnePiece/Products/Booster-Boxes/OP01-Test" title="OP01 Test (English)">OP01 Test again</a>
      </div>
    </body></html>
    """
    results = parse_gallery_page(html, SealedProductType.BOOSTER_BOX)
    assert len(results) == 1


def test_parse_gallery_page_only_from_price():
    """Products with only a From price (no Trend) still produce one price row."""
    html = f"""
    <html><body>
      <div class="col-6">
        <img src="https://static.cardmarket.com/img/op01.jpg" />
        <a href="/en/OnePiece/Products/Booster-Boxes/OP01-Test" title="OP01 Test (English)">OP01 Test</a>
        <dl><dt>From</dt><dd>55,00 €</dd></dl>
      </div>
    </body></html>
    """
    results = parse_gallery_page(html, SealedProductType.BOOSTER_BOX)
    assert len(results) == 1
    _, prices = results[0]
    by_type = _prices_by_type(prices)
    assert SealedPriceType.FROM in by_type
    assert SealedPriceType.TREND not in by_type
    assert by_type[SealedPriceType.FROM].price == pytest.approx(55.00)
