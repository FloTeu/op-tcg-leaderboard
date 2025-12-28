import os
import logging
import time
from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery, storage, firestore
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

credentials = get_credentials()
bq_client = bigquery.Client(credentials=credentials)
storage_client = storage.Client(credentials=credentials)
firestore_client = firestore.Client(credentials=credentials, database="op-leaderboard")



def run_bq_query(query: str, ttl_hours: float | None = None, location: str = "europe-west3") -> list[dict[str, Any]]:
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
        location: BigQuery location (default: europe-west3)
    
    Returns:
        List of dictionaries representing query results
    """
    
    # Select appropriate cache based on TTL
    cache = None
    cache_key = None
    
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
        
        # Check if result is in cache
        if cache_key in cache:
            logging.info(f"Cache hit for query: {query[:100]}...")
            return cache[cache_key]
    
    # Execute query
    t_start = time.time()
    logging.info(f"Running bq query (TTL: {ttl_hours}h): {query}")
    query_job = bq_client.query(query, location=location)
    query_line = query.replace("\n", " ")
    rows_raw = query_job.result()
    logging.info(f"Finished bq query '{query_line[:50]}...{query_line[-50:]}' in {time.time() - t_start:.2f}s")

    
    # Convert to list of dicts. Required for caching to hash the return value.
    rows = [dict(row) for row in rows_raw]
    
    # Cache the result if caching is enabled
    if cache is not None and cache_key is not None:
        cache[cache_key] = rows
    
    return rows