from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_tournament_wins, get_leader_win_rate


def init_load_data():
    """Initially load and cache required data for Leaderboard app"""
    latest_meta = MetaFormat.to_list()[-1]
    # we need historical elo data (all meta formats)
    get_leader_elo_data()
    get_leader_tournament_wins(meta_formats=[latest_meta], only_official=True)
    get_leader_tournament_wins(meta_formats=[latest_meta], only_official=False)
    get_leader_win_rate(meta_formats=[latest_meta])






