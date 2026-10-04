import json

import pytest

from datetime import date

from op_tcg.backend.etl.transform import (
    parse_card_product,
    parse_sealed_product,
    extract_tcgplayer_product_id,
    build_tcgplayer_id_lookup,
    extract_cardnexus_tcgplayer_ids,
    resolve_product_mapping_by_tcgplayer_id,
    extract_cardmarket_id_from_image_url,
    build_cardmarket_sealed_id_lookup,
    resolve_sealed_product_mapping_by_cardmarket_id,
    flatten_price_snapshot,
    flatten_price_history,
)
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace


# --- parse_card_product ---

def test_parse_card_product_full_record():
    product = {
        "id": 12345,
        "printNumber": "OP03-099",
        "name": "Charlotte Katakuri",
        "expansionId": 7,
        "expansionSlug": "op03-pillars-of-strength",
    }
    result = parse_card_product(product, feed_checksum="abc123")
    assert result.product_id == "12345"
    assert result.print_number == "OP03-099"
    assert result.name == "Charlotte Katakuri"
    assert result.expansion_id == "7"
    assert result.expansion_slug == "op03-pillars-of-strength"
    assert result.feed_checksum == "abc123"
    assert json.loads(result.raw_json) == product


def test_parse_card_product_missing_optional_fields():
    product = {"id": 42}
    result = parse_card_product(product, feed_checksum="abc123")
    assert result.product_id == "42"
    assert result.print_number is None
    assert result.name is None
    assert result.expansion_id is None
    assert result.expansion_slug is None


def test_parse_card_product_missing_id_raises():
    with pytest.raises(KeyError):
        parse_card_product({"name": "no id here"}, feed_checksum="abc123")


# --- parse_sealed_product ---

# Real CardNexus catalog sample for a sealed booster box
_BOOSTER_BOX_PRODUCT = {
    "id": 152375, "productType": "sealed", "name": "Pillars of Strength - Booster Box",
    "nameSlug": "pillars-of-strength-booster-box", "slug": "op03-pillars-of-strength-booster-box",
    "expansionId": 17, "expansionSlug": "pillars-of-strength", "printNumber": None, "variant": None,
    "rarity": None, "finishes": ["Standard"], "languages": ["en", "fr", "ja", "ko", "zh-cn"],
    "imageUrl": "https://ik.imagekit.io/cardnexus/production/onepiece/477176boosterbox.png",
    "imageBackUrl": None, "productCategory": "booster_box",
    "externalIds": {"cardmarket": [{"finish": "Standard", "id": 714443}], "tcgplayer": [{"finish": "Standard", "id": 477176}]},
    "translations": {"fr": {"name": "Boîte de Boosters Pillars of Strength"}},
    "attributes": {},
}


def test_parse_sealed_product_full_record():
    result = parse_sealed_product(_BOOSTER_BOX_PRODUCT, feed_checksum="abc123")
    assert result.product_id == "152375"
    assert result.name == "Pillars of Strength - Booster Box"
    assert result.expansion_id == "17"
    assert result.expansion_slug == "pillars-of-strength"
    assert result.product_category == "booster_box"
    assert result.image_url == _BOOSTER_BOX_PRODUCT["imageUrl"]
    assert result.feed_checksum == "abc123"
    assert json.loads(result.raw_json) == _BOOSTER_BOX_PRODUCT


def test_parse_sealed_product_missing_optional_fields():
    result = parse_sealed_product({"id": 1}, feed_checksum="abc123")
    assert result.product_id == "1"
    assert result.name is None
    assert result.expansion_id is None
    assert result.product_category is None
    assert result.image_url is None


def test_parse_sealed_product_missing_id_raises():
    with pytest.raises(KeyError):
        parse_sealed_product({"name": "no id here"}, feed_checksum="abc123")


# --- extract_tcgplayer_product_id ---

def test_extract_tcgplayer_product_id_full_nested_url():
    url = (
        "https://partner.tcgplayer.com/ONEPIECE?u=https%3A%2F%2Fwww.tcgplayer.com%2Fproduct%2F544530"
        "%2Fone-piece-card-game-extra-booster-memorial-collection-tony-tonychopper"
    )
    assert extract_tcgplayer_product_id(url) == "544530"


def test_extract_tcgplayer_product_id_short_form():
    url = "https://partner.tcgplayer.com/ONEPIECE?u=685325-eb04-054"
    assert extract_tcgplayer_product_id(url) == "685325"


def test_extract_tcgplayer_product_id_no_u_param_returns_none():
    assert extract_tcgplayer_product_id("https://www.cardmarket.com/en/OnePiece/Products/Singles/OP01/Foo") is None


def test_extract_tcgplayer_product_id_unparseable_u_param_returns_none():
    assert extract_tcgplayer_product_id("https://partner.tcgplayer.com/ONEPIECE?u=not-an-id") is None


# --- build_tcgplayer_id_lookup ---

def test_build_tcgplayer_id_lookup_maps_id_to_card():
    rows = [
        {"card_id": "OP01-025", "language": "en", "aa_version": 0,
         "url": "https://partner.tcgplayer.com/ONEPIECE?u=685325-op01-025"},
    ]
    lookup = build_tcgplayer_id_lookup(rows)
    assert lookup == {"685325": [("OP01-025", OPTcgLanguage.EN, 0)]}


def test_build_tcgplayer_id_lookup_skips_unparseable_urls():
    rows = [{"card_id": "OP01-025", "language": "en", "aa_version": 0, "url": "https://www.cardmarket.com/x"}]
    assert build_tcgplayer_id_lookup(rows) == {}


def test_build_tcgplayer_id_lookup_multiple_cards_same_id_are_both_kept():
    # Defensive: if two of our rows ever parsed to the same TCGplayer id, both should
    # survive as match candidates rather than one silently overwriting the other.
    rows = [
        {"card_id": "OP01-025", "language": "en", "aa_version": 0,
         "url": "https://partner.tcgplayer.com/ONEPIECE?u=685325-a"},
        {"card_id": "OP01-025", "language": "jp", "aa_version": 0,
         "url": "https://partner.tcgplayer.com/ONEPIECE?u=685325-b"},
    ]
    lookup = build_tcgplayer_id_lookup(rows)
    assert set(lookup["685325"]) == {("OP01-025", OPTcgLanguage.EN, 0), ("OP01-025", OPTcgLanguage.JP, 0)}


# --- extract_cardnexus_tcgplayer_ids ---

def test_extract_cardnexus_tcgplayer_ids_from_real_sample():
    assert extract_cardnexus_tcgplayer_ids(_BOOSTER_BOX_PRODUCT) == ["477176"]


def test_extract_cardnexus_tcgplayer_ids_missing_external_ids():
    assert extract_cardnexus_tcgplayer_ids({"id": 1}) == []


def test_extract_cardnexus_tcgplayer_ids_multiple_finishes():
    product = {"externalIds": {"tcgplayer": [{"finish": "Standard", "id": 1}, {"finish": "Foil", "id": 2}]}}
    assert extract_cardnexus_tcgplayer_ids(product) == ["1", "2"]


# --- resolve_product_mapping_by_tcgplayer_id ---

# Based on the real OP01-025 CardNexus catalog sample
_ZORO_BASE = {
    "id": 12389, "printNumber": "OP01-025", "expansionId": 19,
    "variant": None, "languages": ["en", "fr", "ja", "ko", "zh-cn"],
    "externalIds": {"tcgplayer": [{"finish": "Standard", "id": 685325}]},
}
_ZORO_PARALLEL = {
    "id": 12390, "printNumber": "OP01-025", "expansionId": 19,
    "variant": "Alternate Art", "languages": ["en", "fr", "ja", "ko", "zh-cn"],
    "externalIds": {"tcgplayer": [{"finish": "Standard", "id": 695509}]},
}


def test_resolve_product_mapping_by_tcgplayer_id_unique_match():
    lookup = {"685325": [("OP01-025", OPTcgLanguage.EN, 0)]}
    product = {
        "id": 999, "languages": ["en"],
        "externalIds": {
            "tcgplayer": [{"finish": "Standard", "id": 685325}],
            "cardmarket": [{"finish": "Standard", "id": 714443}],
        },
    }
    mappings = resolve_product_mapping_by_tcgplayer_id(product, lookup)
    assert len(mappings) == 1
    m = mappings[0]
    assert m.language == OPTcgLanguage.EN
    assert m.matched is True
    assert m.card_id == "OP01-025"
    assert m.aa_version == 0
    assert m.match_method == "tcgplayer_id"
    assert m.tcgplayer_id == "685325"
    assert m.cardmarket_id == "714443"


def test_resolve_product_mapping_by_tcgplayer_id_carries_external_ids_even_when_unmatched():
    # Visibility into *why* a product didn't match should still show the id it tried.
    product = {"id": 1, "languages": ["en"], "externalIds": {"tcgplayer": [{"finish": "Standard", "id": 999999}],
                                                              "cardmarket": [{"finish": "Standard", "id": 111111}]}}
    mappings = resolve_product_mapping_by_tcgplayer_id(product, {})
    assert mappings[0].tcgplayer_id == "999999"
    assert mappings[0].cardmarket_id == "111111"


def test_resolve_product_mapping_by_tcgplayer_id_recovers_language_from_lookup_not_product():
    # Base/parallel variants each get their own TCGplayer id, which already pins down
    # the exact aa_version per language — no need for product.languages to assert it.
    lookup = {
        "685325": [("OP01-025", OPTcgLanguage.EN, 0), ("OP01-025", OPTcgLanguage.JP, 0)],
    }
    mappings = resolve_product_mapping_by_tcgplayer_id(_ZORO_BASE, lookup)
    languages = {m.language for m in mappings}
    assert languages == {OPTcgLanguage.EN, OPTcgLanguage.JP}
    assert all(m.matched and m.aa_version == 0 for m in mappings)


def test_resolve_product_mapping_by_tcgplayer_id_no_recognized_language_yields_nothing():
    product = {**_ZORO_BASE, "languages": ["fr", "ko", "zh-cn"]}
    assert resolve_product_mapping_by_tcgplayer_id(product, {}) == []


def test_resolve_product_mapping_by_tcgplayer_id_no_external_id():
    product = {"id": 1, "languages": ["en"], "externalIds": {}}
    mappings = resolve_product_mapping_by_tcgplayer_id(product, {})
    assert len(mappings) == 1
    assert mappings[0].matched is False
    assert mappings[0].match_method == "no_external_id"


def test_resolve_product_mapping_by_tcgplayer_id_no_match_in_our_data():
    product = {"id": 1, "languages": ["en"], "externalIds": {"tcgplayer": [{"finish": "Standard", "id": 999999}]}}
    mappings = resolve_product_mapping_by_tcgplayer_id(product, {})
    assert mappings[0].matched is False
    assert mappings[0].match_method == "no_match"


def test_resolve_product_mapping_by_tcgplayer_id_distinguishes_base_from_parallel():
    lookup = {
        "685325": [("OP01-025", OPTcgLanguage.EN, 0)],
        "695509": [("OP01-025", OPTcgLanguage.EN, 1)],
    }
    base_mappings = resolve_product_mapping_by_tcgplayer_id(_ZORO_BASE, lookup)
    en_base = next(m for m in base_mappings if m.language == OPTcgLanguage.EN)
    assert en_base.aa_version == 0

    parallel_mappings = resolve_product_mapping_by_tcgplayer_id(_ZORO_PARALLEL, lookup)
    en_parallel = next(m for m in parallel_mappings if m.language == OPTcgLanguage.EN)
    assert en_parallel.aa_version == 1


def test_resolve_product_mapping_by_tcgplayer_id_partial_match_mixes_matched_and_unmatched():
    # EN resolves via the lookup; JP is recognized by CardNexus but absent from our data.
    lookup = {"685325": [("OP01-025", OPTcgLanguage.EN, 0)]}
    product = {**_ZORO_BASE, "languages": ["en", "ja"]}
    mappings = resolve_product_mapping_by_tcgplayer_id(product, lookup)
    by_language = {m.language: m for m in mappings}
    assert by_language[OPTcgLanguage.EN].matched is True
    assert by_language[OPTcgLanguage.JP].matched is False
    assert by_language[OPTcgLanguage.JP].match_method == "no_match"


# --- extract_cardmarket_id_from_image_url ---

def test_extract_cardmarket_id_from_image_url_real_shape():
    url = "https://product-images.s3.cardmarket.com/5/LOB/577919/577919.jpg"
    assert extract_cardmarket_id_from_image_url(url) == "577919"


def test_extract_cardmarket_id_from_image_url_no_trailing_number_returns_none():
    assert extract_cardmarket_id_from_image_url("https://static.cardmarket.com/img/op01-booster-en.jpg") is None


# --- build_cardmarket_sealed_id_lookup ---

def test_build_cardmarket_sealed_id_lookup_maps_id_to_product():
    rows = [
        {"id": "op01-romance-dawn-booster-box", "language": "en",
         "image_url": "https://product-images.s3.cardmarket.com/5/OP/714443/714443.jpg"},
    ]
    lookup = build_cardmarket_sealed_id_lookup(rows)
    assert lookup == {"714443": [("op01-romance-dawn-booster-box", OPTcgLanguage.EN)]}


def test_build_cardmarket_sealed_id_lookup_skips_missing_or_unparseable_image_urls():
    rows = [
        {"id": "a", "language": "en", "image_url": None},
        {"id": "b", "language": "en", "image_url": "https://static.cardmarket.com/img/op01.jpg"},
    ]
    assert build_cardmarket_sealed_id_lookup(rows) == {}


# --- resolve_sealed_product_mapping_by_cardmarket_id ---

def test_resolve_sealed_product_mapping_by_cardmarket_id_matches():
    lookup = {"714443": [("op03-pillars-of-strength-booster-box", OPTcgLanguage.EN)]}
    mapping = resolve_sealed_product_mapping_by_cardmarket_id(_BOOSTER_BOX_PRODUCT, lookup)
    assert mapping.matched is True
    assert mapping.match_method == "cardmarket_id"
    assert mapping.sealed_product_id == "op03-pillars-of-strength-booster-box"
    assert mapping.language == OPTcgLanguage.EN
    assert mapping.cardmarket_id == "714443"
    assert mapping.tcgplayer_id == "477176"


def test_resolve_sealed_product_mapping_by_cardmarket_id_no_external_id():
    mapping = resolve_sealed_product_mapping_by_cardmarket_id({"id": 1, "externalIds": {}}, {})
    assert mapping.matched is False
    assert mapping.match_method == "no_external_id"


def test_resolve_sealed_product_mapping_by_cardmarket_id_no_match_in_our_data():
    mapping = resolve_sealed_product_mapping_by_cardmarket_id(_BOOSTER_BOX_PRODUCT, {})
    assert mapping.matched is False
    assert mapping.match_method == "no_match"
    assert mapping.cardmarket_id == "714443"


# --- flatten_price_snapshot ---

def test_flatten_price_snapshot_cardmarket_and_tcgplayer():
    response = {
        "productId": 12345,
        "pricesByFinish": {
            "Standard": {
                "cardmarket": {
                    "currency": "EUR", "low": 1.0, "mid": 2.0, "high": 3.0, "marketValue": 2.5,
                },
                "tcgplayer": {
                    "currency": "USD", "low": 1.5, "mid": None, "high": None, "marketValue": 2.0,
                },
            }
        },
    }
    snapshots = flatten_price_snapshot("12345", response)
    by_marketplace = {s.marketplace: s for s in snapshots}
    assert len(snapshots) == 2

    cm = by_marketplace[OPTcgMarketplace.CARDMARKET]
    assert cm.finish == "Standard"
    assert cm.currency == "EUR"
    assert cm.low == 1.0
    assert cm.mid == 2.0
    assert cm.high == 3.0
    assert cm.market_value == 2.5

    tcg = by_marketplace[OPTcgMarketplace.TCGPLAYER]
    assert tcg.currency == "USD"
    assert tcg.mid is None


def test_flatten_price_snapshot_cardnexus_block_shape():
    response = {
        "pricesByFinish": {
            "Standard": {
                "cardnexus": {
                    "low": {"amount": 0.8, "currency": "EUR"},
                    "listingCount": 5,
                    "availableQuantity": 12,
                    "regions": {},
                },
            }
        },
    }
    snapshots = flatten_price_snapshot("12345", response)
    assert len(snapshots) == 1
    cn = snapshots[0]
    assert cn.marketplace == OPTcgMarketplace.CARD_NEXUS
    assert cn.low == 0.8
    assert cn.currency == "EUR"
    assert cn.mid is None
    assert cn.high is None
    assert cn.market_value is None
    assert json.loads(cn.raw_json)["listingCount"] == 5


def test_flatten_price_snapshot_unknown_marketplace_is_skipped():
    response = {
        "pricesByFinish": {
            "Standard": {
                "some_new_source_not_yet_known": {"low": 1.0},
            }
        },
    }
    assert flatten_price_snapshot("12345", response) == []


def test_flatten_price_snapshot_missing_prices_by_finish():
    assert flatten_price_snapshot("12345", {}) == []


def test_flatten_price_snapshot_null_block_is_skipped():
    response = {"pricesByFinish": {"Standard": {"cardmarket": None}}}
    assert flatten_price_snapshot("12345", response) == []


def test_flatten_price_snapshot_defaults_date_to_today():
    response = {"pricesByFinish": {"Standard": {"cardmarket": {"currency": "EUR", "low": 1.0}}}}
    rows = flatten_price_snapshot("12345", response)
    assert rows[0].date == date.today()


def test_flatten_price_snapshot_accepts_explicit_as_of():
    response = {"pricesByFinish": {"Standard": {"cardmarket": {"currency": "EUR", "low": 1.0}}}}
    explicit_date = date(2026, 1, 1)
    rows = flatten_price_snapshot("12345", response, as_of=explicit_date)
    assert rows[0].date == explicit_date


# --- flatten_price_history ---

def test_flatten_price_history_parses_days():
    response = {
        "productId": 12345,
        "from": "2026-01-01",
        "to": "2026-01-02",
        "data": [
            {"date": "2026-01-01", "marketplace": "cardmarket", "finish": "Standard", "low": 1.0, "mid": 2.0, "high": 3.0, "marketValue": 2.5},
            {"date": "2026-01-02", "marketplace": "tcgplayer", "finish": "Standard", "low": 1.5, "mid": None, "high": None, "marketValue": 2.0},
        ],
    }
    rows = flatten_price_history("12345", response)
    assert len(rows) == 2

    cm = next(r for r in rows if r.marketplace == OPTcgMarketplace.CARDMARKET)
    assert cm.date == date(2026, 1, 1)
    assert cm.currency == "EUR"
    assert cm.low == 1.0
    assert cm.market_value == 2.5

    tcg = next(r for r in rows if r.marketplace == OPTcgMarketplace.TCGPLAYER)
    assert tcg.date == date(2026, 1, 2)
    assert tcg.currency == "USD"
    assert tcg.mid is None


def test_flatten_price_history_missing_data_key():
    assert flatten_price_history("12345", {}) == []


def test_flatten_price_history_skips_unknown_marketplace():
    response = {"data": [{"date": "2026-01-01", "marketplace": "some_new_source", "low": 1.0}]}
    assert flatten_price_history("12345", response) == []


def test_flatten_price_history_skips_malformed_date():
    response = {"data": [{"date": "not-a-date", "marketplace": "cardmarket", "low": 1.0}]}
    assert flatten_price_history("12345", response) == []


def test_flatten_price_history_defaults_finish_to_standard():
    response = {"data": [{"date": "2026-01-01", "marketplace": "cardmarket", "low": 1.0}]}
    rows = flatten_price_history("12345", response)
    assert rows[0].finish == "Standard"
