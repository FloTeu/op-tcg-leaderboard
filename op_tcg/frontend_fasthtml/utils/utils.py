import os
import json
import base64
import logging
from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery, storage
from fastcore.xtras import timed_cache

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

@timed_cache(seconds=60*60*6) # 6 hours
def run_bq_query(query: str) -> list[dict[str, Any]]:
    """Runs a bigquery query
    Uses timed_cache to only rerun when the query changes or after 60 min.
    """
    logging.info(f"Running bq query: {query}")
    query_job = bq_client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for caching to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows