import subprocess
from pathlib import Path
import streamlit as st
from op_tcg.frontend.utils.extract import get_leader_elo_data, get_leader_tournament_wins, get_leader_win_rate, \
    get_card_data, get_card_popularity_data, get_leader_extended, get_tournament_standing_data, \
    get_tournament_decklist_data, get_all_tournament_decklist_data
from op_tcg.frontend.utils.meta_format import get_latest_released_meta_format_with_data


def init_load_data():
    """Initially load and cache required data for Leaderboard app"""
    latest_meta = get_latest_released_meta_format_with_data()
    # we need historical elo data (all meta formats)
    get_leader_elo_data()
    get_leader_tournament_wins(meta_formats=[latest_meta])
    get_leader_win_rate(meta_formats=[latest_meta])
    get_all_tournament_decklist_data()
    get_leader_extended()
    get_card_data()
    get_card_popularity_data()

def build_frontend():
    """Initially ensures frontend is builded
    Cached in order to be only executed once"""
    with st.spinner("Build frontend"):
        frontend_build = Path(st.__path__[0]).parent / "streamlit_elements/frontend/build"
        if not frontend_build.exists():
            subprocess.run(['python', 'build_frontend.py'], check=True)






