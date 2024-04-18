# streamlit_app.py
from pathlib import Path

import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery

import op_tcg
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.matches import MatchResult, BQMatch, BQLeaderElo, BQLeaderElos
from op_tcg.backend.etl.extract import get_leader_ids

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)

# Perform query.
# Uses st.cache_data to only rerun when the query changes or after 10 min.
@st.cache_data(ttl=600)
def run_query(query):
    query_job = client.query(query, location="europe-west3")
    rows_raw = query_job.result()
    # Convert to list of dicts. Required for st.cache_data to hash the return value.
    rows = [dict(row) for row in rows_raw]
    return rows

def main():
    meta_formats: list[MetaFormat] = st.sidebar.multiselect("Meta", [MetaFormat.OP01, MetaFormat.OP02, MetaFormat.OP03, MetaFormat.OP04, MetaFormat.OP05, MetaFormat.OP06], default=MetaFormat.OP06)

    rows = run_query(f"""
    SELECT
      *
    FROM
      `op-tcg-leaderboard-dev.matches.leader_elo`
    order by elo desc
    """)


    # Print results.
    st.write("Elo of all leaders")
    # Iterate over elo rating
    leader_elos=[]
    for row in rows:
        leader_elo = BQLeaderElo(**row)
        leader_elos.append(leader_elo)
    df = BQLeaderElos(elo_ratings=leader_elos).to_dataframe()
    st.table(df[df["meta_format"].isin(meta_formats)])

if __name__ == "__main__":
    main()