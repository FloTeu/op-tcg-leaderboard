import os
import logging
import threading
import time
from typing import Any
from google.oauth2 import service_account
from functools import cache

from google.cloud import bigquery
from op_tcg.frontend.utils.cache import _CACHE_1D, _CACHE_6H, _CACHE_1H, _CACHE_30M


# Create API client using credentials
def get_credentials():
    """Get Google Cloud credentials.

    Prioritizes local file via GCP_CREDENTIALS env var.
    Falls back to Application Default Credentials (ADC) if not set,
    which works automatically on Cloud Run.
    """
    # 1. Try local file (for development)
    service_key_path = os.environ.get("GCP_CREDENTIALS")
    if service_key_path:
        if os.path.exists(service_key_path):
            try:
                return service_account.Credentials.from_service_account_file(service_key_path)
            except Exception as e:
                logging.warning(f"Failed to load credentials from {service_key_path}: {e}")
        else:
            logging.warning(f"GCP_CREDENTIALS set to {service_key_path} but file does not exist")

    # 2. Fallback to ADC (for Cloud Run / Production)
    return None

@cache
def get_bq_client() -> bigquery.Client:
    """Creates the BigQuery client on first use, so importing this module needs no Google credentials (e.g. in tests)."""
    return bigquery.Client(credentials=get_credentials())


# Cache keys of queries currently running, so concurrent calls of the same query wait for its result instead of running it again
_pending_queries: set[str] = set()
_pending_queries_condition = threading.Condition()


def run_bq_query(query: str, ttl_hours: float | None = None, location: str = "europe-west1") -> list[dict[str, Any]]:
    """
    Runs a bigquery query with configurable TTL caching
    
    Args:
        query: The BigQuery SQL query string
        ttl_hours: Cache TTL in hours. Common values:
                   - 24.0: Static/reference data (leader info, card data)
                   - 6.0: Default for most queries
                   - 1.0: Frequently changing data 
                   - 0.5: Real-time data
                   - None: No caching
        location: BigQuery location (default: europe-west1)
    
    Returns:
        List of dictionaries representing query results
    """
    
    # Select appropriate cache based on TTL
    if ttl_hours is not None:
        if ttl_hours >= 24:
            cache = _CACHE_1D
        elif ttl_hours >= 6:
            cache = _CACHE_6H
        elif ttl_hours >= 1:
            cache = _CACHE_1H
        else:
            cache = _CACHE_30M
            
        # Create cache key that includes TTL to prevent conflicts
        cache_key = f"{query}|ttl_{ttl_hours}"

        with _pending_queries_condition:
            # Wait if the same query is already running in another thread, then use its cached result
            _pending_queries_condition.wait_for(lambda: cache_key not in _pending_queries)
            if cache_key in cache:
                logging.info(f"Cache hit for query: {query[:100]}...")
                return cache[cache_key]
            _pending_queries.add(cache_key)
        try:
            rows = _execute_bq_query(query, location, ttl_hours)
            with _pending_queries_condition:
                cache[cache_key] = rows
            return rows
        finally:
            with _pending_queries_condition:
                _pending_queries.discard(cache_key)
                _pending_queries_condition.notify_all()

    return _execute_bq_query(query, location, ttl_hours)


def _execute_bq_query(query: str, location: str, ttl_hours: float | None) -> list[dict[str, Any]]:
    t_start = time.time()
    logging.info(f"Running bq query (TTL: {ttl_hours}h): {query}")
    query_job = get_bq_client().query(query, location=location)
    query_line = query.replace("\n", " ")
    rows_raw = query_job.result()
    logging.info(f"Finished bq query '{query_line[:50]}...{query_line[-50:]}' in {time.time() - t_start:.2f}s")

    
    # Convert to list of dicts. Required for caching to hash the return value.
    return [dict(row) for row in rows_raw]