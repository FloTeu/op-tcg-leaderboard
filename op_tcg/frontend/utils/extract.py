import streamlit as st
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader, TournamentWinner, LeaderElo
from op_tcg.backend.models.matches import Match, LeaderWinRate
from op_tcg.backend.models.tournaments import TournamentStanding, Tournament, TournamentStandingExtended
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

def get_leader_win_rate(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[LeaderWinRate]:
    bq_win_rates: list[LeaderWinRate] = []
    for meta_format in meta_formats:
        # cached for each session
        win_rate_data_rows = run_bq_query(f"""SELECT * FROM `{st.secrets["gcp_service_account"]["project_id"]}.{LeaderWinRate.get_dataset_id()}.{LeaderWinRate.__tablename__}` where meta_format = '{meta_format}'""")
        bq_win_rates.extend([LeaderWinRate(**d) for d in win_rate_data_rows])

    if leader_ids:
        return [bqwr for bqwr in bq_win_rates if (bqwr.leader_id in leader_ids)]
    else:
        return bq_win_rates

def get_tournament_standing_data(meta_formats: list[MetaFormat], leader_id: list[str]) -> list[TournamentStandingExtended]:
    bq_tournament_standings: list[TournamentStandingExtended] = []
    for meta_format in meta_formats:
        # cached for each session
        tournament_standing_rows = run_bq_query(f"""
SELECT t1.*, t2.* EXCEPT (create_timestamp, name) FROM `{st.secrets["gcp_service_account"]["project_id"]}.matches.{TournamentStanding.__tablename__}` t1
left join `{st.secrets["gcp_service_account"]["project_id"]}.matches.{Tournament.__tablename__}` t2
on t1.tournament_id = t2.id
where t2.meta_format = '{meta_format}' and t1.leader_id = '{leader_id}'
""")
        bq_tournament_standings.extend([TournamentStandingExtended(**d) for d in tournament_standing_rows])

    return bq_tournament_standings

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
