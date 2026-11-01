from unittest.mock import MagicMock

import pandas as pd

from op_tcg.backend.etl import classes
from op_tcg.backend.etl.classes import CardNexusPriceUpdateEtlJob


def _job(monkeypatch, **kwargs) -> CardNexusPriceUpdateEtlJob:
    monkeypatch.setattr(classes.bigquery, "Client", MagicMock())
    job = CardNexusPriceUpdateEtlJob(cardnexus_client=MagicMock(), **kwargs)
    job.bq_client.query_and_wait.return_value.to_dataframe.return_value = pd.DataFrame({"product_id": ["p1"]})
    return job


def test_candidate_query_excludes_products_already_priced_today(monkeypatch):
    job = _job(monkeypatch, max_requests=550)

    assert job.extract() == ["p1"]

    query = job.bq_client.query_and_wait.call_args.args[0]
    assert "s.last_priced IS NULL OR s.last_priced < CURRENT_DATE()" in query
    assert "LIMIT 550" in query


# --- CardNexusPriceHistoryEtlJob ---

def _history_job(monkeypatch, product_ids: list[str], **kwargs) -> classes.CardNexusPriceHistoryEtlJob:
    monkeypatch.setattr(classes.bigquery, "Client", MagicMock())
    monkeypatch.setattr(classes, "bq_upsert_rows", MagicMock())
    job = classes.CardNexusPriceHistoryEtlJob(cardnexus_client=MagicMock(), **kwargs)
    job.bq_client.query_and_wait.return_value.to_dataframe.return_value = pd.DataFrame({"product_id": product_ids})
    return job


def test_history_candidate_query_filters_by_min_days_without_limit(monkeypatch):
    job = _history_job(monkeypatch, ["p1"], min_history_days=30)

    job.extract()

    query = job.bq_client.query_and_wait.call_args.args[0]
    assert "COALESCE(h.history_days, 0) < 30" in query
    assert "LIMIT" not in query


def test_history_run_in_batches_upserts_each_batch_and_sums_counts(monkeypatch):
    job = _history_job(monkeypatch, ["p1", "p2", "p3"], min_history_days=30)
    monkeypatch.setattr(classes, "flatten_price_history", lambda product_id, response: [product_id] * 2)
    job.cardnexus_client.get_price_history.side_effect = [{}, RuntimeError("429"), {}]

    total_rows = job.run_in_batches(batch_size=2)

    assert total_rows == 4
    assert [c.args[0] for c in classes.bq_upsert_rows.call_args_list] == [["p1", "p1"], ["p3", "p3"]]
    assert (job.requested_count, job.failed_count) == (3, 1)


def test_history_run_in_batches_with_nothing_to_do(monkeypatch):
    job = _history_job(monkeypatch, [], min_history_days=30)

    assert job.run_in_batches() == 0
    assert (job.requested_count, job.failed_count) == (0, 0)
    classes.bq_upsert_rows.assert_not_called()
