import threading
import time
from concurrent.futures import ThreadPoolExecutor
from uuid import uuid4

import pytest

from op_tcg.backend.models.input import MetaFormat, SideMetaFormat
from op_tcg.frontend.utils import utils
from op_tcg.frontend.utils import side_meta_format as smf


@pytest.fixture
def slow_query(monkeypatch):
    """Replaces the BigQuery call by a slow fake, recording the executed queries."""
    executed = []
    lock = threading.Lock()

    def execute(query, location, ttl_hours):
        with lock:
            executed.append(query)
        time.sleep(0.2)
        if query.startswith("FAIL") and executed.count(query) == 1:
            raise RuntimeError("query failed")
        return [{"query": query}]

    monkeypatch.setattr(utils, "_execute_bq_query", execute)
    return executed


def _run_parallel(fn, args_list):
    with ThreadPoolExecutor(max_workers=len(args_list)) as pool:
        return [f.result() if not f.exception() else f.exception() for f in [pool.submit(fn, *a) for a in args_list]]


def test_concurrent_same_query_runs_once(slow_query):
    query = f"SELECT {uuid4()}"
    results = _run_parallel(utils.run_bq_query, [(query, 6.0)] * 5)
    assert slow_query == [query]
    assert all(r == [{"query": query}] for r in results)


def test_different_queries_run_in_parallel(slow_query):
    queries = [f"SELECT {uuid4()}" for _ in range(4)]
    start = time.perf_counter()
    _run_parallel(utils.run_bq_query, [(q, 6.0) for q in queries])
    assert sorted(slow_query) == sorted(queries)
    # 4 queries of 0.2s each would take 0.8s if they were serialized
    assert time.perf_counter() - start < 0.6


def test_waiting_call_retries_if_running_query_fails(slow_query):
    query = f"FAIL {uuid4()}"
    results = _run_parallel(utils.run_bq_query, [(query, 6.0)] * 2)
    assert slow_query == [query, query]
    assert sum(isinstance(r, RuntimeError) for r in results) == 1
    assert [{"query": query}] in results


def test_uncached_queries_are_not_deduplicated(slow_query):
    query = f"SELECT {uuid4()}"
    _run_parallel(utils.run_bq_query, [(query, None)] * 2)
    assert slow_query == [query, query]


def test_cached_function_is_computed_once_for_concurrent_calls(monkeypatch):
    smf.get_side_meta_format_tournament_ids.cache.clear()
    calls = []

    def slow_tournaments(meta_formats):
        calls.append(meta_formats)
        time.sleep(0.2)
        return []

    monkeypatch.setattr(smf, "get_all_tournament_extened_data", slow_tournaments)
    monkeypatch.setattr(smf, "get_all_tournament_decklist_data", lambda: [])
    _run_parallel(smf.get_side_meta_format_tournament_ids, [(MetaFormat.OP17, SideMetaFormat.EB05)] * 4)
    assert len(calls) == 1
    smf.get_side_meta_format_tournament_ids.cache.clear()
