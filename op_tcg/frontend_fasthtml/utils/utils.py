import os
import json
import base64
import logging
from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery, storage, firestore
from op_tcg.frontend_fasthtml.utils.cache import _CACHE_1D, _CACHE_6H, _CACHE_1H, _CACHE_30M


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
    logging.info(f"Running bq query (TTL: {ttl_hours}h): {query}")
    query_job = bq_client.query(query, location=location)
    rows_raw = query_job.result()
    
    # Convert to list of dicts. Required for caching to hash the return value.
    rows = [dict(row) for row in rows_raw]
    
    # Cache the result if caching is enabled
    if cache is not None and cache_key is not None:
        cache[cache_key] = rows
    
    return rows