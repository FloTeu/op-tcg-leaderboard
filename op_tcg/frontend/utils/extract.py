import streamlit as st
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader, TournamentWinner, LeaderElo
from op_tcg.backend.models.matches import Match
from op_tcg.frontend.utils.utils import run_bq_query


def get_leader_data() -> list[Leader]:
    # cached for each session
    leader_data_rows = run_bq_query(f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.{BQDataset.LEADERS}.{Leader.__tablename__}`""")
    bq_leaders = [Leader(**d) for d in leader_data_rows]
    return bq_leaders


def get_match_data(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[Match]:
    bq_matches: list[Match] = []
    for meta_format in meta_formats:
        # cached for each session
        match_data_rows = run_bq_query(f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.matches.{Match.__tablename__}` where meta_format = '{meta_format}'""")
        bq_matches.extend([Match(**d) for d in match_data_rows])

    if leader_ids:
        return [bqm for bqm in bq_matches if (bqm.leader_id in leader_ids)]
    else:
        return bq_matches


def get_leader_elo_data(meta_formats: list[MetaFormat] | None=None) -> list[LeaderElo]:
    """First element is leader with best elo.
    """
    bq_leader_elos: list[LeaderElo] = []
    if meta_formats:
        for meta_format in meta_formats:
            # cached for each session
            leader_elo_rows = run_bq_query(f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.matches.leader_elo` where meta_format = '{meta_format}' order by elo desc""")
            bq_leader_elos.extend([LeaderElo(**d) for d in leader_elo_rows])
    else:
        leader_elo_rows = run_bq_query(
            f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.matches.leader_elo` order by elo desc""")
        bq_leader_elos.extend([LeaderElo(**d) for d in leader_elo_rows])
    return bq_leader_elos


def get_leader_tournament_wins(meta_formats: list[MetaFormat] | None=None, only_official: bool = True) -> list[TournamentWinner]:
    """First element is leader with best elo.
    """
    table_id = "tournament_winner_only_official" if only_official else "tournament_winner_all"
    bq_leader_tournament_wins: list[TournamentWinner] = []
    if meta_formats:
        for meta_format in meta_formats:
            # cached for each session
            leader_wins_rows = run_bq_query(f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.leaders.{table_id}` where meta_format = '{meta_format}'""")
            bq_leader_tournament_wins.extend([TournamentWinner(**d) for d in leader_wins_rows])
    else:
        leader_wins_rows = run_bq_query(
            f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.leaders.{table_id}`""")
        bq_leader_tournament_wins.extend([TournamentWinner(**d) for d in leader_wins_rows])
    return bq_leader_tournament_wins
