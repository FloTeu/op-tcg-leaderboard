import streamlit as st

from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery, storage

from op_tcg.backend.models.storage import StorageBucket

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
bq_client = bigquery.Client(credentials=credentials)
storage_client = storage.Client(credentials=credentials)


@st.cache_data(ttl=60*60, show_spinner=False)
def run_bq_query(query: str) -> list[dict[str, Any]]:
    """Runs a bigquery query
    Uses st.cache_data to only rerun when the query changes or after 60 min.
    """
    query_job = bq_client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows

def upload2gcp_storage(path_to_file: str, blob_name: str, bucket: str = StorageBucket.PUBLIC_BUCKET, content_type: str | None = None):
    bucket = storage_client.get_bucket(bucket)
    blob = bucket.blob(blob_name)
    blob.upload_from_filename(path_to_file, content_type=content_type)

