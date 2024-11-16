from op_tcg.backend.utils.utils import timeit
from op_tcg.frontend.fix_streamlit_elements import patch_streamlit_elements
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_tournament_wins, get_leader_win_rate, \
    get_card_data, get_card_popularity_data, get_leader_extended, get_tournament_standing_data, \
    get_tournament_decklist_data, get_all_tournament_decklist_data
from op_tcg.frontend.utils.meta_format import get_latest_released_meta_format_with_data
from op_tcg.backend.models.input import MetaFormat


@timeit
def init_load_data():
    """Initially load and cache required data for Leaderboard app"""
    latest_meta = get_latest_released_meta_format_with_data()
    # we need historical elo data (all meta formats)
    get_leader_elo_data()
    get_leader_tournament_wins(meta_formats=[latest_meta])
    get_leader_win_rate(meta_formats=MetaFormat.to_list(only_after_release=True))
    get_all_tournament_decklist_data()
    get_leader_extended()
    get_card_data()
    get_card_popularity_data()





