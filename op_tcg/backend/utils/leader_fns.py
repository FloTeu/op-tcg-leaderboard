import pandera as pa
from pandera.typing import DataFrame

from op_tcg.backend.models.matches import Match, LeaderWinRate


def df_win_rate_data2lid_dicts(df_win_rate_data: DataFrame[LeaderWinRate.paSchema()], leader_ids: list[str] | None = None) -> tuple[dict[str, float], dict[str, float]]:
    """Returns leader id 2 win rate dict and leader id 2 match count dict as tuple
    If leader_ids is provided, its ensured that all leader ids are contained in the output dicts
    """
    leader_ids: list[str] = leader_ids or []
    lid2win_rate: dict[str, float] = {}
    lid2match_count: dict[str, int] = {}

    def calculate_win_rate(df_lid_results):
        lid = df_lid_results.iloc[0].leader_id
        num_matches = df_lid_results.total_matches.sum()
        weighted_average = (df_lid_results['win_rate'] * df_lid_results['total_matches']).sum() / df_lid_results['total_matches'].sum()

        # fill output dicts
        lid2win_rate[lid] = float("%.2f" % (weighted_average))
        lid2match_count[lid] = num_matches

    df_win_rate_data.groupby(["leader_id"]).apply(calculate_win_rate)

    # fill up leader ids with no matches yet
    for lid in leader_ids:
        if lid not in lid2win_rate:
            lid2win_rate[lid] = 0.0
        if lid not in lid2match_count:
            lid2match_count[lid] = 0

    return lid2win_rate, lid2match_count



def df_match_data2lid_dicts(df_match_data: DataFrame[Match.paSchema()]) -> tuple[dict[str, float], dict[str, float]]:
    """Returns lid 2 win rate dict and lid 2 match count dict as tuple"""
    lid2win_rate: dict[str, float] = {}
    lid2match_count: dict[str, int] = {}


    def calculate_win_rate(df_lid_results):
        lid = df_lid_results.iloc[0].leader_id
        num_matches = len(df_lid_results)
        num_wins = len(df_lid_results.query("result == 2"))
        if num_matches == 0 or num_wins == 0:
            lid2win_rate[lid] = 0.0
        else:
            lid2win_rate[lid] = float("%.2f" % (num_wins / num_matches))
        lid2match_count[lid] = num_matches

    df_match_data.groupby(["leader_id"]).apply(calculate_win_rate)
    return lid2win_rate, lid2match_count

def lid2win_rate(leader_id: str, df_meta_match_data: DataFrame[Match.paSchema()]) -> float:
    result_counts = df_meta_match_data.query(f"leader_id == '{leader_id}'").groupby("result").count()["id"]
    if 2 not in result_counts.index:
        return 0.0
    else:
        return float("%.2f" % (result_counts.loc[2] / result_counts.sum()))
