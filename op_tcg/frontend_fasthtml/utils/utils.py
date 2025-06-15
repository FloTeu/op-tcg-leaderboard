import os
import json
import base64
import time
import hashlib
from typing import Any, Dict, Optional
from google.oauth2 import service_account
from google.cloud import bigquery, storage

# Module-level cache that persists across function calls within the same instance
_QUERY_CACHE: Dict[str, Dict[str, Any]] = {}
_CACHE_TTL = 60 * 60 * 2  # 2 hours in seconds

def _get_cache_key(query: str) -> str:
    """Generate a cache key from the query string."""
    return hashlib.md5(query.encode()).hexdigest()

def _is_cache_valid(cache_entry: Dict[str, Any]) -> bool:
    """Check if a cache entry is still valid."""
    return time.time() - cache_entry['timestamp'] < _CACHE_TTL

def _get_from_cache(query: str) -> Optional[list[dict[str, Any]]]:
    """Get query result from cache if available and valid."""
    cache_key = _get_cache_key(query)
    if cache_key in _QUERY_CACHE:
        cache_entry = _QUERY_CACHE[cache_key]
        if _is_cache_valid(cache_entry):
            return cache_entry['data']
        else:
            # Remove expired entry
            del _QUERY_CACHE[cache_key]
    return None

def _store_in_cache(query: str, data: list[dict[str, Any]]) -> None:
    """Store query result in cache."""
    cache_key = _get_cache_key(query)
    _QUERY_CACHE[cache_key] = {
        'data': data,
        'timestamp': time.time()
    }

# Create API client using base64 encoded service account key
def get_credentials():
    """Get Google Cloud credentials from base64 encoded service account key"""
    service_key_b64 = os.environ.get("GOOGLE_SERVICE_KEY")
    if not service_key_b64:
        raise ValueError("GOOGLE_SERVICE_KEY environment variable is not set")
    
    try:
        # Decode base64 string to get JSON
        service_key_json = base64.b64decode(service_key_b64).decode('utf-8')
        service_account_info = json.loads(service_key_json)
        
        # Create credentials from service account info
        credentials = service_account.Credentials.from_service_account_info(service_account_info)
        return credentials
    except Exception as e:
        raise ValueError(f"Failed to decode GOOGLE_SERVICE_KEY: {e}")

credentials = get_credentials()
bq_client = bigquery.Client(credentials=credentials)
storage_client = storage.Client(credentials=credentials)

def run_bq_query(query: str) -> list[dict[str, Any]]:
    """
    Runs a bigquery query with serverless-compatible caching.
    Uses module-level cache that persists within the same function instance.
    """
    import logging
    
    # Try to get from cache first
    cached_result = _get_from_cache(query)
    if cached_result is not None:
        logging.info(f"Using cached result for query: {query[:100]}...")
        return cached_result
    
    # Execute query if not in cache
    logging.info(f"Running bq query: {query}")
    query_job = bq_client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts
    rows = [dict(row) for row in rows_raw]
    
    # Store in cache
    _store_in_cache(query, rows)
    logging.info(f"Cached query result for: {query[:100]}...")
    
    return rows