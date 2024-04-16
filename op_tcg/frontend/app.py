# streamlit_app.py
from pathlib import Path

import streamlit as st
from google.oauth2 import service_account
from google.cloud import bigquery

import op_tcg
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.matches import MatchResult, BQMatch
from op_tcg.backend.etl.extract import get_leader_ids

# Create API client.
credentials = service_account.Credentials.from_service_account_info(
    st.secrets["gcp_service_account"]
)
client = bigquery.Client(credentials=credentials)


# TODO: Move this somewhere else in backend
def calculate_elo_change(current_elo, opponent_elo, result: MatchResult, k_factor=32):
    expected_score = 1 / (1 + 10 ** ((opponent_elo - current_elo) / 400))
    # TODO: check if the calculation is correct
    actual_score = result.value / 2  # WIN=1, DRAW=0.5, LOSE=0
    elo_change = k_factor * (actual_score - expected_score)
    return elo_change


# Initialize Elo ratings
all_leader_ids = get_leader_ids(Path(op_tcg.__file__).parent.parent / "data" / "limitless")
elo_ratings = {leader_id: 1000 for leader_id in all_leader_ids}

# Now elo_ratings contains the updated Elo scores for each leader


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
    rows = run_query(f"""
    SELECT
      *
    FROM
      `op-tcg-leaderboard-dev.matches.matches`
    WHERE meta_format = '{MetaFormat.OP02}'
    ORDER BY
      timestamp ASC;
    """)

    # Iterate over matches
    for row in rows:
        match = BQMatch(**row)
        leader_elo = elo_ratings[match.leader_id]
        opponent_elo = elo_ratings[match.opponent_id]

        # Calculate Elo change
        leader_elo_change = calculate_elo_change(leader_elo, opponent_elo, match.result)
        opponent_elo_change = calculate_elo_change(opponent_elo, leader_elo, MatchResult(1 - match.result.value))

        # Update Elo ratings
        elo_ratings[match.leader_id] += leader_elo_change
        elo_ratings[match.opponent_id] += opponent_elo_change

    # Print results.
    st.write("Elo of all leaders")
    for leader_id, elo_score in elo_ratings.items():
        st.write(f"Leader {leader_id}: {elo_score}")

