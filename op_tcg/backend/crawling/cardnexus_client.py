"""Rate-limited client for the CardNexus public API.

Docs: https://docs.cardnexus.com/pricing/index.md

The CardNexus API is still under active development — endpoint response shapes
may change without notice. This client is deliberately defensive: it never
assumes a nested field is present, and callers are expected to keep the raw
response around (see op_tcg.backend.models.cardnexus) rather than relying
solely on parsed fields.

Rate limits (per docs, per account not per key):
  - 60 requests/minute globally across all endpoints
  - 600 requests/hour on /products/{id}/prices
  - 120 requests/hour on /products/{id}/prices/history
A 429 response includes a `Retry-After` header (seconds) which is honored directly.
"""
import gzip
import io
import json
import logging
import os
import time
from collections import deque
from typing import Iterator

import requests

logger = logging.getLogger(__name__)

API_BASE = "https://public-api.cardnexus.com/v1"

GLOBAL_BUCKET = "global"
PRICES_BUCKET = "prices"
HISTORY_BUCKET = "history"

# (limit, window_seconds) per bucket
_BUCKET_LIMITS: dict[str, tuple[int, float]] = {
    GLOBAL_BUCKET: (60, 60.0),
    PRICES_BUCKET: (600, 3600.0),
    HISTORY_BUCKET: (120, 3600.0),
}


class CardNexusRateLimiter:
    """Sleep-based sliding-window rate limiter, one window per bucket.

    Paces requests to stay under the limit rather than bursting and handling
    429s, per CardNexus's own recommended client pattern.
    """

    def __init__(self, time_fn=time.monotonic, sleep_fn=time.sleep):
        self._time_fn = time_fn
        self._sleep_fn = sleep_fn
        self._history: dict[str, deque] = {bucket: deque() for bucket in _BUCKET_LIMITS}

    def acquire(self, bucket: str) -> None:
        if bucket not in _BUCKET_LIMITS:
            return
        limit, window = _BUCKET_LIMITS[bucket]
        history = self._history[bucket]
        while True:
            now = self._time_fn()
            while history and now - history[0] >= window:
                history.popleft()
            if len(history) < limit:
                history.append(now)
                return
            wait = window - (now - history[0])
            if wait > 0:
                logger.debug("Rate limit bucket '%s' full, sleeping %.2fs", bucket, wait)
                self._sleep_fn(wait)


class CardNexusApiError(RuntimeError):
    """Raised when a CardNexus request fails after exhausting retries."""


class CardNexusClient:
    def __init__(
        self,
        api_key: str | None = None,
        base_url: str = API_BASE,
        session: requests.Session | None = None,
        rate_limiter: CardNexusRateLimiter | None = None,
        sleep_fn=time.sleep,
    ):
        import dotenv
        dotenv.load_dotenv()
        self.api_key = api_key or os.environ["CARDNEXUS_API_KEY"]
        self.base_url = base_url
        self.session = session or requests.Session()
        self.rate_limiter = rate_limiter or CardNexusRateLimiter()
        self._sleep_fn = sleep_fn

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}"}

    def _request(
        self,
        method: str,
        path: str,
        params: dict | None = None,
        bucket: str = GLOBAL_BUCKET,
        max_retries: int = 5,
    ) -> requests.Response:
        last_exc: Exception | None = None
        backoff = 2.0
        for attempt in range(1, max_retries + 1):
            self.rate_limiter.acquire(GLOBAL_BUCKET)
            if bucket != GLOBAL_BUCKET:
                self.rate_limiter.acquire(bucket)

            resp = self.session.request(
                method, f"{self.base_url}{path}", headers=self._headers(), params=params, timeout=30,
            )

            if resp.status_code == 429:
                retry_after = float(resp.headers.get("Retry-After", backoff))
                logger.warning("CardNexus 429 for %s (attempt %d/%d) — sleeping %.1fs", path, attempt, max_retries, retry_after)
                self._sleep_fn(retry_after)
                continue

            if resp.status_code >= 500:
                logger.warning("CardNexus %d for %s (attempt %d/%d) — sleeping %.1fs", resp.status_code, path, attempt, max_retries, backoff)
                last_exc = requests.HTTPError(f"{resp.status_code} for {path}")
                self._sleep_fn(backoff)
                backoff *= 2
                continue

            resp.raise_for_status()
            return resp

        raise CardNexusApiError(f"Exhausted {max_retries} retries for {path}") from last_exc

    def get_catalog_feed_meta(self, game_id: str = "onepiece") -> dict:
        return self._request("GET", f"/feeds/{game_id}/catalog").json()

    def iter_catalog_products(self, game_id: str = "onepiece") -> Iterator[dict]:
        """Stream and decompress the bulk catalog feed, yielding one dict per record.

        Malformed lines are logged and skipped rather than aborting the whole feed —
        the feed is large and a single bad record shouldn't lose the rest.
        """
        meta = self.get_catalog_feed_meta(game_id)
        feed_url = meta["url"]

        resp = self.session.get(feed_url, stream=True, timeout=60)
        resp.raise_for_status()
        # Feed is served with Content-Encoding: gzip; disable transparent decoding so
        # we get the untouched .ndjson.gz bytes and decompress them ourselves.
        resp.raw.decode_content = False
        raw_bytes = resp.raw.read()

        skipped = 0
        with gzip.open(io.BytesIO(raw_bytes), "rt", encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    skipped += 1
                    logger.warning("Skipping malformed catalog feed line: %s", exc)
        if skipped:
            logger.warning("Skipped %d malformed catalog feed line(s)", skipped)

    def get_current_prices(self, product_id: str) -> dict:
        return self._request("GET", f"/products/{product_id}/prices", bucket=PRICES_BUCKET).json()

    def get_price_history(
        self,
        product_id: str,
        marketplace: str | None = None,
        finish: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
    ) -> dict:
        """Daily price history for a product. Dates are ISO 'YYYY-MM-DD' strings.

        Per CardNexus docs: range span is capped at 365 days, and days without a
        snapshot are simply absent from the result (no need to handle gaps specially).
        """
        params = {}
        if marketplace:
            params["marketplace"] = marketplace
        if finish:
            params["finish"] = finish
        if from_date:
            params["from"] = from_date
        if to_date:
            params["to"] = to_date
        return self._request(
            "GET", f"/products/{product_id}/prices/history", params=params, bucket=HISTORY_BUCKET,
        ).json()
