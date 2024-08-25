import streamlit as st

from typing import Any
from google.oauth2 import service_account
from google.cloud import bigquery, storage

from op_tcg.backend.models.input import MetaFormat

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

def sort_df_by_meta_format(df, meta_format_col: str = "meta_format", reverse=False):
    sorted_meta_formats = MetaFormat.to_list()
    if reverse:
        sorted_meta_formats.reverse()
    order_mapping = {meta_format: idx for idx, meta_format in enumerate(sorted_meta_formats)}
    df['sort_order'] = df[meta_format_col].map(order_mapping)
    return df.sort_values('sort_order').drop(columns='sort_order')