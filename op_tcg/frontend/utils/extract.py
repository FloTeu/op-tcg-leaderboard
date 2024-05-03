from op_tcg.backend.models.bq import BQDataset
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.leader import Leader
from op_tcg.backend.models.matches import Match, LeaderElo
from op_tcg.frontend.utils.utils import run_bq_query


def get_leader_data() -> list[Leader]:
    # cached for each session
    leader_data_rows = run_bq_query(f"SELECT * FROM `op-tcg-leaderboard-dev.{BQDataset.LEADERS}.{Leader.__tablename__}`")
    bq_leaders = [Leader(**d) for d in leader_data_rows]
    return bq_leaders


def get_match_data(meta_formats: list[MetaFormat], leader_ids: list[str] | None = None) -> list[Match]:
    bq_matches: list[Match] = []
    for meta_format in meta_formats:
        # cached for each session
        match_data_rows = run_bq_query(f"SELECT * FROM `op-tcg-leaderboard-dev.matches.{Match.__tablename__}` where meta_format = '{meta_format}'")
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
            leader_elo_rows = run_bq_query(f"SELECT * FROM `op-tcg-leaderboard-dev.matches.leader_elo` where meta_format = '{meta_format}' order by elo desc")
            bq_leader_elos.extend([LeaderElo(**d) for d in leader_elo_rows])
    else:
        leader_elo_rows = run_bq_query(
            f"SELECT * FROM `op-tcg-leaderboard-dev.matches.leader_elo` order by elo desc")
        bq_leader_elos.extend([LeaderElo(**d) for d in leader_elo_rows])
    return bq_leader_elos