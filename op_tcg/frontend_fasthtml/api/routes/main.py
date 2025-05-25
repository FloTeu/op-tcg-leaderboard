from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.leader import LeaderboardSortBy
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table
from op_tcg.frontend_fasthtml.utils.launch import init_load_data
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict, get_filtered_leaders
from op_tcg.frontend_fasthtml.pages.leader import create_leader_content, HX_INCLUDE
from op_tcg.frontend_fasthtml.api.models import LeaderboardSort, LeaderDataParams

# Import route setups from other modules
from op_tcg.frontend_fasthtml.api.routes import (
    tournaments,
    decklists,
    filters,
    matchups,
    charts,
    pages,
    stats,
    similar,
    card_movement
)

DATA_IS_LOADED = False


def setup_api_routes(rt):
    # Setup routes from other modules
    pages.setup_api_routes(rt)
    charts.setup_api_routes(rt)
    tournaments.setup_api_routes(rt)
    decklists.setup_api_routes(rt)
    filters.setup_api_routes(rt)
    matchups.setup_api_routes(rt)
    stats.setup_api_routes(rt)
    similar.setup_api_routes(rt)
    card_movement.setup_api_routes(rt)

    @rt("/api/launch")
    def launch_data(request: Request):
        global DATA_IS_LOADED
        if not DATA_IS_LOADED:
            init_load_data()
            DATA_IS_LOADED = True
        return {"data_is_loaded": DATA_IS_LOADED}
