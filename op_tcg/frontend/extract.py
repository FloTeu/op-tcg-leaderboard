from op_tcg.backend.models.leader import BQLeader
from op_tcg.frontend.utils import run_bq_query


def get_leader_data() -> list[BQLeader]:
    # cached for each session
    leader_data_rows = run_bq_query("SELECT * FROM `op-tcg-leaderboard-dev.leaders.leaders`")
    bq_leaders = [BQLeader(**d) for d in leader_data_rows]
    return bq_leaders