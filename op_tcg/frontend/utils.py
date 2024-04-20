import streamlit as st

from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)


@st.cache_data(ttl=60*60)
def run_bq_query(query: str) -> list[dict[str, Any]]:
    """Runs a bigquery query
    Uses st.cache_data to only rerun when the query changes or after 60 min.
    """
    query_job = client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows
