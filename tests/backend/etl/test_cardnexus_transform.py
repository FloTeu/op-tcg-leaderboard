import json

import pytest

from op_tcg.backend.etl.transform import (
    parse_card_product,
    parse_sealed_product,
    compute_expansion_release_set_matches,
    resolve_product_language_mapping,
    flatten_price_snapshot,
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


# --- compute_expansion_release_set_matches ---

def test_compute_expansion_release_set_matches_identical_sets():
    card_ids = {f"OP01-{i:03d}" for i in range(1, 21)}
    expansion_to_card_ids = {"exp-romance-dawn": card_ids}
    release_set_to_card_ids = {"OP01": card_ids}
    result = compute_expansion_release_set_matches(expansion_to_card_ids, release_set_to_card_ids, min_set_size=5)
    assert result == {"exp-romance-dawn": ("OP01", pytest.approx(1.0))}


def test_compute_expansion_release_set_matches_below_threshold_is_unmatched():
    base = {f"OP01-{i:03d}" for i in range(1, 21)}
    # Only half overlap -> Jaccard of 0.5, below an explicit 0.8 threshold
    expansion_to_card_ids = {"exp-romance-dawn": {f"OP01-{i:03d}" for i in range(1, 11)}}
    release_set_to_card_ids = {"OP01": base}
    result = compute_expansion_release_set_matches(
        expansion_to_card_ids, release_set_to_card_ids, min_jaccard=0.8, min_set_size=5,
    )
    assert result == {}


def test_compute_expansion_release_set_matches_promo_catchall_does_not_falsely_match():
    # Mirrors the real CardNexus "one-piece-promotion-cards" bucket: a small
    # release_set's ids are a strict subset of a much larger catch-all expansion.
    # A containment-style score would call this a match; Jaccard should not.
    small_release_set = {"P-001", "P-002"}
    giant_promo_expansion = small_release_set | {f"P-{i:03d}" for i in range(3, 200)}
    result = compute_expansion_release_set_matches(
        {"exp-promos": giant_promo_expansion},
        {"promo-set-a": small_release_set},
        min_set_size=2,
    )
    assert result == {}


def test_compute_expansion_release_set_matches_respects_min_set_size():
    tiny_ids = {"OP01-001", "OP01-002"}
    result = compute_expansion_release_set_matches(
        {"exp-tiny": tiny_ids}, {"tiny-set": tiny_ids}, min_set_size=5,
    )
    assert result == {}


def test_compute_expansion_release_set_matches_picks_best_of_multiple_candidates():
    card_ids = {f"OP01-{i:03d}" for i in range(1, 21)}
    almost_same = card_ids - {"OP01-001"} | {"OP99-999"}
    expansion_to_card_ids = {"exp-romance-dawn": card_ids}
    release_set_to_card_ids = {"OP01": card_ids, "OP01-near-dupe": almost_same, "unrelated": {"X-1", "X-2", "X-3", "X-4", "X-5"}}
    result = compute_expansion_release_set_matches(expansion_to_card_ids, release_set_to_card_ids, min_set_size=5)
    assert result["exp-romance-dawn"][0] == "OP01"


# --- resolve_product_language_mapping ---

# Based on the real OP01-025 CardNexus catalog sample
_ZORO_BASE = {
    "id": 12389, "printNumber": "OP01-025", "expansionId": 19,
    "variant": None, "languages": ["en", "fr", "ja", "ko", "zh-cn"],
}
_ZORO_PARALLEL = {
    "id": 12390, "printNumber": "OP01-025", "expansionId": 19,
    "variant": "Alternate Art", "languages": ["en", "fr", "ja", "ko", "zh-cn"],
}
_EXPANSION_TO_RELEASE_SET = {"19": "romance-dawn"}


def test_resolve_product_language_mapping_unique_candidate():
    candidates_lookup = {("OP01-025", "romance-dawn", OPTcgLanguage.EN): [0]}
    product = {"id": 999, "printNumber": "OP01-025", "expansionId": 19, "variant": None, "languages": ["en"]}
    mappings = resolve_product_language_mapping(product, _EXPANSION_TO_RELEASE_SET, candidates_lookup)
    assert len(mappings) == 1
    m = mappings[0]
    assert m.language == OPTcgLanguage.EN
    assert m.matched is True
    assert m.card_id == "OP01-025"
    assert m.aa_version == 0
    assert m.match_method == "unique"


def test_resolve_product_language_mapping_produces_one_row_per_recognized_language():
    # fr/ko/zh-cn aren't tracked (only en/ja are) -> should be silently dropped
    candidates_lookup = {
        ("OP01-025", "romance-dawn", OPTcgLanguage.EN): [0],
        ("OP01-025", "romance-dawn", OPTcgLanguage.JP): [0],
    }
    mappings = resolve_product_language_mapping(_ZORO_BASE, _EXPANSION_TO_RELEASE_SET, candidates_lookup)
    languages = {m.language for m in mappings}
    assert languages == {OPTcgLanguage.EN, OPTcgLanguage.JP}


def test_resolve_product_language_mapping_no_recognized_language_yields_nothing():
    product = {**_ZORO_BASE, "languages": ["fr", "ko", "zh-cn"]}
    assert resolve_product_language_mapping(product, _EXPANSION_TO_RELEASE_SET, {}) == []


def test_resolve_product_language_mapping_missing_print_number():
    product = {"id": 1, "printNumber": None, "expansionId": 19, "variant": None, "languages": ["en"]}
    mappings = resolve_product_language_mapping(product, _EXPANSION_TO_RELEASE_SET, {})
    assert len(mappings) == 1
    assert mappings[0].matched is False
    assert mappings[0].match_method == "no_print_number"


def test_resolve_product_language_mapping_no_release_match():
    product = {"id": 1, "printNumber": "OP01-025", "expansionId": 999, "variant": None, "languages": ["en"]}
    mappings = resolve_product_language_mapping(product, {}, {})
    assert mappings[0].matched is False
    assert mappings[0].match_method == "no_release_match"


def test_resolve_product_language_mapping_no_candidates_in_release():
    candidates_lookup = {}
    product = {"id": 1, "printNumber": "OP01-025", "expansionId": 19, "variant": None, "languages": ["en"]}
    mappings = resolve_product_language_mapping(product, _EXPANSION_TO_RELEASE_SET, candidates_lookup)
    assert mappings[0].matched is False
    assert mappings[0].match_method == "no_match"


def test_resolve_product_language_mapping_variant_pair_base_and_parallel():
    # Two aa_versions in the same (card_id, release_set, language): base (lower) + parallel
    candidates_lookup = {("OP01-025", "romance-dawn", OPTcgLanguage.EN): [0, 1]}

    base_mappings = resolve_product_language_mapping(_ZORO_BASE, _EXPANSION_TO_RELEASE_SET, candidates_lookup)
    en_base = next(m for m in base_mappings if m.language == OPTcgLanguage.EN)
    assert en_base.matched is True
    assert en_base.aa_version == 0
    assert en_base.match_method == "variant_pair"

    parallel_mappings = resolve_product_language_mapping(_ZORO_PARALLEL, _EXPANSION_TO_RELEASE_SET, candidates_lookup)
    en_parallel = next(m for m in parallel_mappings if m.language == OPTcgLanguage.EN)
    assert en_parallel.matched is True
    assert en_parallel.aa_version == 1
    assert en_parallel.match_method == "variant_pair"


def test_resolve_product_language_mapping_three_or_more_candidates_is_ambiguous():
    candidates_lookup = {("OP01-025", "romance-dawn", OPTcgLanguage.EN): [0, 1, 2]}
    mappings = resolve_product_language_mapping(_ZORO_PARALLEL, _EXPANSION_TO_RELEASE_SET, candidates_lookup)
    en = next(m for m in mappings if m.language == OPTcgLanguage.EN)
    assert en.matched is False
    assert en.match_method == "ambiguous_variant"


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
