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
    # Create a copy of the DataFrame to avoid SettingWithCopyWarning
    df = df.copy()

    sorted_meta_formats = MetaFormat.to_list()
    if reverse:
        sorted_meta_formats.reverse()
    order_mapping = {meta_format: idx for idx, meta_format in enumerate(sorted_meta_formats)}
    df.loc[:, 'sort_order'] = df[meta_format_col].map(order_mapping)
    return df.sort_values('sort_order').drop(columns='sort_order')

def merge_dicts(dict1, dict2):
    """
    Recursively merges two dictionaries.
    Values from dict2 overwrite those in dict1 if they exist.
    Lists are merged by updating elements if they are dictionaries.
    """
    for key, value in dict2.items():
        if isinstance(value, dict) and key in dict1 and isinstance(dict1[key], dict):
            # If both values are dictionaries, merge them recursively
            merge_dicts(dict1[key], value)
        elif isinstance(value, list) and key in dict1 and isinstance(dict1[key], list):
            # If both values are lists, merge them
            for i, item in enumerate(value):
                if i < len(dict1[key]) and isinstance(item, dict) and isinstance(dict1[key][i], dict):
                    # If both list elements are dictionaries, merge them
                    merge_dicts(dict1[key][i], item)
                elif i < len(dict1[key]):
                    # Otherwise, replace the item
                    dict1[key][i] = item
                else:
                    # Append new items from dict2
                    dict1[key].append(item)
        else:
            # Otherwise, overwrite the value in dict1 with the value from dict2
            dict1[key] = value
    return dict1

def get_anchor_link(text: str) -> str:
    """Tries to apply streamlit logic to transform a text into a anchor link"""
    return text.lower().replace(" ", "-").replace("(", "").replace(")", "")