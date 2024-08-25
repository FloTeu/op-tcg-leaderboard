from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_tournament_wins, get_leader_win_rate, \
    get_card_data, get_card_popularity_data, get_leader_extended, get_tournament_standing_data, \
    get_tournament_decklist_data, get_all_tournament_decklist_data


def init_load_data():
    """Initially load and cache required data for Leaderboard app"""
    latest_meta = MetaFormat.to_list()[-1]
    # we need historical elo data (all meta formats)
    get_leader_elo_data()
    get_leader_tournament_wins(meta_formats=[latest_meta])
    get_leader_win_rate(meta_formats=[latest_meta])
    get_all_tournament_decklist_data()
    get_leader_extended()
    get_card_data()
    get_card_popularity_data()






