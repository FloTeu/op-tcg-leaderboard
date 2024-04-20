import streamlit as st

from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.matches import BQLeaderElo, BQLeaderElos
from op_tcg.frontend.utils import run_bq_query


def main():
    meta_formats: list[MetaFormat] = st.sidebar.multiselect("Meta", [MetaFormat.OP01, MetaFormat.OP02, MetaFormat.OP03, MetaFormat.OP04, MetaFormat.OP05, MetaFormat.OP06], default=MetaFormat.OP06)

    rows = run_bq_query(f"""
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