import json

import pytest

from op_tcg.backend.etl.transform import (
    parse_catalog_product,
    match_catalog_product_to_card,
    flatten_price_snapshot,
)
from op_tcg.backend.models.cards import OPTcgLanguage, OPTcgMarketplace


# --- parse_catalog_product ---

def test_parse_catalog_product_full_record():
    product = {
        "id": 12345,
        "printNumber": "OP03-099",
        "name": "Charlotte Katakuri",
        "expansionId": 7,
        "expansionSlug": "op03-pillars-of-strength",
    }
    result = parse_catalog_product(product, feed_checksum="abc123")
    assert result.product_id == "12345"
    assert result.print_number == "OP03-099"
    assert result.name == "Charlotte Katakuri"
    assert result.expansion_id == "7"
    assert result.expansion_slug == "op03-pillars-of-strength"
    assert result.feed_checksum == "abc123"
    assert json.loads(result.raw_json) == product


def test_parse_catalog_product_missing_optional_fields():
    product = {"id": 42}
    result = parse_catalog_product(product, feed_checksum="abc123")
    assert result.product_id == "42"
    assert result.print_number is None
    assert result.name is None
    assert result.expansion_id is None
    assert result.expansion_slug is None


def test_parse_catalog_product_missing_id_raises():
    with pytest.raises(KeyError):
        parse_catalog_product({"name": "no id here"}, feed_checksum="abc123")


# --- match_catalog_product_to_card ---

def test_match_catalog_product_to_card_unique_match():
    cards_by_id = {"OP03-099": [(OPTcgLanguage.EN, 0)]}
    mapping = match_catalog_product_to_card("12345", "OP03-099", cards_by_id)
    assert mapping.matched is True
    assert mapping.card_id == "OP03-099"
    assert mapping.language == OPTcgLanguage.EN
    assert mapping.aa_version == 0
    assert mapping.match_method == "print_number_unique"


def test_match_catalog_product_to_card_no_print_number():
    mapping = match_catalog_product_to_card("12345", None, {})
    assert mapping.matched is False
    assert mapping.match_method == "no_print_number"


def test_match_catalog_product_to_card_no_match():
    mapping = match_catalog_product_to_card("12345", "OP99-999", {"OP03-099": [(OPTcgLanguage.EN, 0)]})
    assert mapping.matched is False
    assert mapping.match_method == "no_match"


def test_match_catalog_product_to_card_ambiguous():
    cards_by_id = {"OP03-099": [(OPTcgLanguage.EN, 0), (OPTcgLanguage.EN, 1)]}
    mapping = match_catalog_product_to_card("12345", "OP03-099", cards_by_id)
    assert mapping.matched is False
    assert mapping.match_method == "ambiguous_print_number"
    assert mapping.card_id is None


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
