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
