# Import route setups from other modules
from op_tcg.frontend.api.routes import (
    tournaments,
    decklists,
    filters,
    matchups,
    charts,
    pages,
    stats,
    similar,
    card_movement,
    prices,
    watchlist
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
    prices.setup_api_routes(rt)
    watchlist.setup_watchlist_routes(rt)
