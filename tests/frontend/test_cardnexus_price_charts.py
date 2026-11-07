from datetime import date
from unittest.mock import MagicMock

import pytest

from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend.utils import charts, extract


@pytest.fixture
def bq(monkeypatch):
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "test-project")
    mock = MagicMock(return_value=[])
    monkeypatch.setattr(extract, "run_bq_query", mock)
    return mock


# --- extract ---

def test_card_cardnexus_prices_split_by_marketplace_currency(bq):
    bq.return_value = [
        {"marketplace": "cardmarket", "date": date(2026, 10, 30), "price": 1.5},
        {"marketplace": "tcgplayer", "date": date(2026, 10, 30), "price": 2.0},
    ]

    result = extract.get_cardnexus_card_price_development_data("OP01-025", days=30, aa_version=1)

    assert result == {"eur": [{"date": "2026-10-30", "price": 1.5}], "usd": [{"date": "2026-10-30", "price": 2.0}]}
    query = bq.call_args.args[0]
    assert "test-project.cards.card_nexus_price_view" in query
    assert "card_id = 'OP01-025'" in query
    assert "AND aa_version = 1" in query
    assert "INTERVAL 30 DAY" in query


def test_card_cardnexus_prices_empty_when_view_missing(bq):
    bq.side_effect = RuntimeError("Not found: card_nexus_price_view")

    assert extract.get_cardnexus_card_price_development_data("OP01-025") == {"eur": [], "usd": []}


@pytest.mark.parametrize("currency,marketplace", [
    (CardCurrency.EURO, "cardmarket"),
    (CardCurrency.US_DOLLAR, "tcgplayer"),
])
def test_sealed_cardnexus_prices_only_from_matched_mapping(bq, currency, marketplace):
    bq.return_value = [{"date": date(2026, 10, 30), "price": 99.0}]

    result = extract.get_cardnexus_sealed_price_history("sealed-1", currency, days=90)

    assert result == [{"date": "2026-10-30", "price": 99.0}]
    query = bq.call_args.args[0]
    assert "m.matched" in query
    assert "m.sealed_product_id = 'sealed-1'" in query
    assert f"p.marketplace = '{marketplace}'" in query


def test_sealed_cardnexus_prices_empty_on_error(bq):
    bq.side_effect = RuntimeError("Not found")

    assert extract.get_cardnexus_sealed_price_history("sealed-1", CardCurrency.EURO) == []


# --- chart builders ---

@pytest.fixture
def chart_config(monkeypatch):
    captured = {}

    def fake_script(chart_type, container_id, config):
        captured.update(config)
        return ""

    monkeypatch.setattr(charts, "_create_chart_script", fake_script)
    return captured


def test_card_chart_merges_cardnexus_series_by_date(chart_config):
    charts.create_price_development_chart("c", {
        "eur": [{"date": "2026-10-01", "price": 1.0}],
        "usd": [],
        "cardnexus_eur": [{"date": "2026-10-01", "price": 1.1}, {"date": "2026-10-02", "price": 1.2}],
        "cardnexus_usd": [{"date": "2026-10-02", "price": 1.3}],
    })

    assert chart_config["data"] == [
        {"date": "2026-10-01", "eur_price": 1.0, "usd_price": None,
         "cardnexus_eur_price": 1.1, "cardnexus_usd_price": None},
        {"date": "2026-10-02", "eur_price": None, "usd_price": None,
         "cardnexus_eur_price": 1.2, "cardnexus_usd_price": 1.3},
    ]


def test_card_chart_without_cardnexus_match_keeps_existing_series(chart_config):
    charts.create_price_development_chart("c", {"eur": [{"date": "2026-10-01", "price": 1.0}], "usd": []})

    assert chart_config["data"] == [{"date": "2026-10-01", "eur_price": 1.0, "usd_price": None,
                                     "cardnexus_eur_price": None, "cardnexus_usd_price": None}]


def test_sealed_chart_adds_cardnexus_series(chart_config):
    charts.create_sealed_price_development_chart("s", {
        "from": [{"date": "2026-10-01", "price": 80.0}],
        "trend": [],
        "cardnexus": [{"date": "2026-10-02", "price": 85.0}],
    })

    assert chart_config["data"] == [
        {"date": "2026-10-01", "from_price": 80.0, "trend_price": None, "cardnexus_price": None},
        {"date": "2026-10-02", "from_price": None, "trend_price": None, "cardnexus_price": 85.0},
    ]
