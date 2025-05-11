
import os
from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery, storage
from fastcore.xtras import timed_cache

# Create API client.
credentials = service_account.Credentials.from_service_account_file(
     os.environ.get("GCP_CREDENTIALS")
)
bq_client = bigquery.Client(credentials=credentials)
storage_client = storage.Client(credentials=credentials)

@timed_cache(seconds=60*60) # 1 hour
def run_bq_query(query: str) -> list[dict[str, Any]]:
    """Runs a bigquery query
    Uses timed_cache to only rerun when the query changes or after 60 min.
    """
    query_job = bq_client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows