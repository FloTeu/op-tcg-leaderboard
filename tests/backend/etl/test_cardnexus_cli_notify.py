from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from click.testing import CliRunner

from op_tcg.cli import etl as etl_cli


@pytest.fixture
def notify(monkeypatch):
    mock = MagicMock()
    monkeypatch.setattr(etl_cli, "notify_job_result", mock)
    return mock


def _fake_job_class(monkeypatch, name: str, run_result=None, run_error=None, **attrs):
    job = MagicMock(**attrs)
    if run_error:
        job.run.side_effect = run_error
    else:
        job.run.return_value = run_result
    monkeypatch.setattr(etl_cli, name, MagicMock(return_value=job))
    return job


def _invoke(*args):
    return CliRunner().invoke(etl_cli.cardnexus_group, list(args))


# --- sync-catalog ---

def test_sync_catalog_notifies_match_counts(monkeypatch, notify):
    card_mappings = [SimpleNamespace(matched=True), SimpleNamespace(matched=False)]
    sealed_mappings = [SimpleNamespace(matched=True)]
    _fake_job_class(monkeypatch, "CardNexusCatalogSyncEtlJob",
                    run_result=(["c1"], card_mappings, ["s1"], sealed_mappings))

    result = _invoke("sync-catalog")

    assert result.exit_code == 0
    notify.assert_called_once()
    args, kwargs = notify.call_args
    assert args[0] == "cardnexus-sync-catalog"
    assert kwargs["success"] is True
    assert "1/2 card/language rows matched" in kwargs["summary"]
    assert "1/1 matched" in kwargs["summary"]


def test_sync_catalog_notifies_skip_when_checksum_unchanged(monkeypatch, notify):
    _fake_job_class(monkeypatch, "CardNexusCatalogSyncEtlJob", run_result=([], [], [], []))

    _invoke("sync-catalog")

    assert notify.call_args.kwargs["success"] is True
    assert "skipped" in notify.call_args.kwargs["summary"]


def test_sync_catalog_notifies_failure_and_reraises(monkeypatch, notify):
    _fake_job_class(monkeypatch, "CardNexusCatalogSyncEtlJob", run_error=RuntimeError("boom"))

    result = _invoke("sync-catalog")

    assert result.exit_code != 0
    assert notify.call_args.kwargs["success"] is False
    assert notify.call_args.kwargs["error"] == "boom"


# --- update-prices ---

def test_update_prices_notifies_row_and_failure_counts(monkeypatch, notify):
    _fake_job_class(monkeypatch, "CardNexusPriceUpdateEtlJob", run_result=["r1", "r2", "r3"],
                    requested_count=10, failed_count=2)

    result = _invoke("update-prices")

    assert result.exit_code == 0
    args, kwargs = notify.call_args
    assert args[0] == "cardnexus-update-prices"
    assert kwargs["success"] is True
    assert kwargs["summary"] == "3 price rows from 8/10 products, 2 failed"


def test_update_prices_reports_failure_when_every_request_failed(monkeypatch, notify):
    _fake_job_class(monkeypatch, "CardNexusPriceUpdateEtlJob", run_result=[], requested_count=5, failed_count=5)

    _invoke("update-prices")

    assert notify.call_args.kwargs["success"] is False


def test_price_job_with_nothing_to_do_is_success(monkeypatch, notify):
    _fake_job_class(monkeypatch, "CardNexusPriceUpdateEtlJob", run_result=[], requested_count=0, failed_count=0)

    _invoke("update-prices")

    assert notify.call_args.kwargs["success"] is True


def test_price_job_notifies_failure_and_reraises(monkeypatch, notify):
    _fake_job_class(monkeypatch, "CardNexusPriceUpdateEtlJob", run_error=RuntimeError("quota"))

    result = _invoke("update-prices")

    assert result.exit_code != 0
    assert notify.call_args.kwargs["success"] is False
    assert notify.call_args.kwargs["error"] == "quota"


# --- update-price-history (local batched backfill) ---

def _fake_history_job(monkeypatch, **attrs):
    job = MagicMock(**attrs)
    job_class = MagicMock(return_value=job)
    monkeypatch.setattr(etl_cli, "CardNexusPriceHistoryEtlJob", job_class)
    return job_class, job


def test_update_price_history_runs_in_batches_and_notifies(monkeypatch, notify):
    job_class, job = _fake_history_job(monkeypatch, requested_count=10, failed_count=2)
    job.run_in_batches.return_value = 40

    result = _invoke("update-price-history", "--min-days", "20", "--batch-size", "50")

    assert result.exit_code == 0
    assert job_class.call_args.kwargs["min_history_days"] == 20
    assert job_class.call_args.kwargs["max_requests"] is None
    job.run_in_batches.assert_called_once_with(batch_size=50)
    args, kwargs = notify.call_args
    assert args[0] == "cardnexus-update-price-history"
    assert kwargs["success"] is True
    assert kwargs["summary"] == "40 price rows from 8/10 products, 2 failed"


def test_update_price_history_notifies_failure_and_reraises(monkeypatch, notify):
    _, job = _fake_history_job(monkeypatch)
    job.run_in_batches.side_effect = RuntimeError("bq down")

    result = _invoke("update-price-history")

    assert result.exit_code != 0
    assert notify.call_args.kwargs["success"] is False
    assert notify.call_args.kwargs["error"] == "bq down"
