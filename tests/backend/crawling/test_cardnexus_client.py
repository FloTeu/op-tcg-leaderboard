import gzip
import io
import json
from unittest.mock import Mock

import pytest

from op_tcg.backend.crawling.cardnexus_client import (
    CardNexusClient,
    CardNexusRateLimiter,
    CardNexusApiError,
    GLOBAL_BUCKET,
    PRICES_BUCKET,
    HISTORY_BUCKET,
)


# --- CardNexusRateLimiter ---

class FakeClock:
    def __init__(self):
        self.now = 0.0
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        self.now += seconds


def test_rate_limiter_allows_requests_under_limit():
    clock = FakeClock()
    limiter = CardNexusRateLimiter(time_fn=clock.time, sleep_fn=clock.sleep)
    for _ in range(60):
        limiter.acquire(GLOBAL_BUCKET)
    assert clock.sleeps == []


def test_rate_limiter_sleeps_when_bucket_full():
    clock = FakeClock()
    limiter = CardNexusRateLimiter(time_fn=clock.time, sleep_fn=clock.sleep)
    for _ in range(60):
        limiter.acquire(GLOBAL_BUCKET)
    limiter.acquire(GLOBAL_BUCKET)
    assert len(clock.sleeps) == 1
    assert clock.sleeps[0] == pytest.approx(60.0, rel=1e-6)


def test_rate_limiter_buckets_are_independent():
    clock = FakeClock()
    limiter = CardNexusRateLimiter(time_fn=clock.time, sleep_fn=clock.sleep)
    for _ in range(600):
        limiter.acquire(PRICES_BUCKET)
    assert clock.sleeps == []
    limiter.acquire(GLOBAL_BUCKET)
    assert clock.sleeps == []


# --- CardNexusClient._request ---

def _make_client(monkeypatch, sleeps=None):
    monkeypatch.setenv("CARDNEXUS_API_KEY", "test-key")
    client = CardNexusClient(sleep_fn=(sleeps.append if sleeps is not None else (lambda s: None)))
    client.rate_limiter = CardNexusRateLimiter(time_fn=lambda: 0.0, sleep_fn=lambda s: None)
    return client


def _mock_response(status_code=200, json_data=None, headers=None):
    resp = Mock()
    resp.status_code = status_code
    resp.headers = headers or {}
    resp.json.return_value = json_data or {}
    if status_code >= 400:
        import requests
        resp.raise_for_status.side_effect = requests.HTTPError(f"{status_code}")
    else:
        resp.raise_for_status.side_effect = None
    return resp


def test_request_success_first_try(monkeypatch):
    client = _make_client(monkeypatch)
    client.session = Mock()
    client.session.request.return_value = _mock_response(200, {"ok": True})
    resp = client._request("GET", "/some/path")
    assert resp.json() == {"ok": True}
    assert client.session.request.call_count == 1


def test_request_retries_on_429_honoring_retry_after(monkeypatch):
    sleeps = []
    client = _make_client(monkeypatch, sleeps=sleeps)
    client.session = Mock()
    client.session.request.side_effect = [
        _mock_response(429, headers={"Retry-After": "3"}),
        _mock_response(200, {"ok": True}),
    ]
    resp = client._request("GET", "/some/path", bucket=PRICES_BUCKET)
    assert resp.json() == {"ok": True}
    assert sleeps == [3.0]


def test_request_retries_on_5xx_with_backoff(monkeypatch):
    sleeps = []
    client = _make_client(monkeypatch, sleeps=sleeps)
    client.session = Mock()
    client.session.request.side_effect = [
        _mock_response(503),
        _mock_response(503),
        _mock_response(200, {"ok": True}),
    ]
    resp = client._request("GET", "/some/path")
    assert resp.json() == {"ok": True}
    assert sleeps == [2.0, 4.0]


def test_request_raises_after_exhausting_retries(monkeypatch):
    client = _make_client(monkeypatch, sleeps=[])
    client.session = Mock()
    client.session.request.return_value = _mock_response(503)
    with pytest.raises(CardNexusApiError):
        client._request("GET", "/some/path", max_retries=2)


def test_request_does_not_retry_on_4xx_other_than_429(monkeypatch):
    import requests
    client = _make_client(monkeypatch)
    client.session = Mock()
    client.session.request.return_value = _mock_response(404)
    with pytest.raises(requests.HTTPError):
        client._request("GET", "/some/path")
    assert client.session.request.call_count == 1


# --- iter_catalog_products ---

def _gzip_ndjson(lines: list[str]) -> bytes:
    buf = io.BytesIO()
    with gzip.GzipFile(fileobj=buf, mode="wb") as f:
        f.write("\n".join(lines).encode("utf-8"))
    return buf.getvalue()


def test_iter_catalog_products_yields_parsed_records(monkeypatch):
    client = _make_client(monkeypatch)
    client._request = Mock(return_value=Mock(json=Mock(return_value={"url": "https://example.com/feed.ndjson.gz"})))

    records = [{"id": 1, "printNumber": "OP01-001"}, {"id": 2, "printNumber": "OP01-002"}]
    gz_bytes = _gzip_ndjson([json.dumps(r) for r in records])

    feed_resp = Mock()
    feed_resp.raise_for_status.side_effect = None
    feed_resp.raw = io.BytesIO(gz_bytes)
    feed_resp.raw.decode_content = True

    client.session = Mock()
    client.session.get.return_value = feed_resp

    result = list(client.iter_catalog_products())
    assert result == records
    # transparent decode must be disabled so we control decompression ourselves
    assert feed_resp.raw.decode_content is False


def test_iter_catalog_products_skips_malformed_lines(monkeypatch):
    client = _make_client(monkeypatch)
    client._request = Mock(return_value=Mock(json=Mock(return_value={"url": "https://example.com/feed.ndjson.gz"})))

    good_record = {"id": 1, "printNumber": "OP01-001"}
    gz_bytes = _gzip_ndjson([json.dumps(good_record), "{not valid json", ""])

    feed_resp = Mock()
    feed_resp.raise_for_status.side_effect = None
    feed_resp.raw = io.BytesIO(gz_bytes)
    feed_resp.raw.decode_content = True

    client.session = Mock()
    client.session.get.return_value = feed_resp

    result = list(client.iter_catalog_products())
    assert result == [good_record]


# --- get_price_history ---

def test_get_price_history_builds_params_and_uses_history_bucket(monkeypatch):
    client = _make_client(monkeypatch)
    client.session = Mock()
    client.session.request.return_value = _mock_response(200, {"productId": 12345, "data": []})

    result = client.get_price_history("12345", marketplace="cardmarket", finish="Standard", from_date="2026-01-01", to_date="2026-01-31")

    assert result == {"productId": 12345, "data": []}
    _, kwargs = client.session.request.call_args
    assert kwargs["params"] == {
        "marketplace": "cardmarket", "finish": "Standard", "from": "2026-01-01", "to": "2026-01-31",
    }
    assert "/products/12345/prices/history" in client.session.request.call_args[0][1]


def test_get_price_history_omits_unset_params(monkeypatch):
    client = _make_client(monkeypatch)
    client.session = Mock()
    client.session.request.return_value = _mock_response(200, {"data": []})

    client.get_price_history("12345")

    _, kwargs = client.session.request.call_args
    assert kwargs["params"] == {}


def test_history_bucket_rate_limited_independently():
    clock = FakeClock()
    limiter = CardNexusRateLimiter(time_fn=clock.time, sleep_fn=clock.sleep)
    for _ in range(120):
        limiter.acquire(HISTORY_BUCKET)
    assert clock.sleeps == []
    limiter.acquire(HISTORY_BUCKET)
    assert len(clock.sleeps) == 1
