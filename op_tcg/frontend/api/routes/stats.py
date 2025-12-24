from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.extract import get_leader_extended, get_tournament_decklist_data
from op_tcg.frontend.api.models import LeaderDataParams

def setup_api_routes(rt):
    @rt("/api/leader-stats")
    async def get_leader_stats(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get leader data with meta format region filtering
        leader_data_list = get_leader_extended(
            meta_formats=params.meta_format, 
            leader_ids=[params.lid],
            meta_format_region=params.region
        )
        
        # Filter list by official, but include leaders without match data (only_official is None)
        leader_data_list = [
            ld for ld in leader_data_list 
            if ld.only_official == params.only_official or ld.only_official is None
        ]

        if not leader_data_list:
            return ft.P("No stats available for this leader.", cls="text-red-400")
        
        # Calculate stats, handling cases where data might be None
        leaders_with_win_rate = [ld for ld in leader_data_list if ld.win_rate is not None]
        leaders_with_matches = [ld for ld in leader_data_list if ld.total_matches is not None]
        leaders_with_elo = [ld for ld in leader_data_list if ld.elo is not None]
        
        # Calculate means
        total_win_rate = None
        if leaders_with_win_rate:
            total_win_rate = sum(ld.win_rate for ld in leaders_with_win_rate) / len(leaders_with_win_rate)
        
        total_matches = None
        if leaders_with_matches:
            total_matches = sum(ld.total_matches for ld in leaders_with_matches)
        
        total_tournament_wins = sum(ld.tournament_wins for ld in leader_data_list)
        
        total_elo = None
        if leaders_with_elo:
            total_elo = int(sum(ld.elo for ld in leaders_with_elo) / len(leaders_with_elo))

        # Calculate mean deck price
        decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            leader_ids=[params.lid],
            meta_format_region=params.region
        )

        mean_price_eur = None
        if decklists:
            prices_eur = [d.price_eur for d in decklists if hasattr(d, 'price_eur') and d.price_eur > 0]
            if prices_eur:
                mean_price_eur = sum(prices_eur) / len(prices_eur)

        return ft.Div(
            ft.P(f"Win Rate: {total_win_rate * 100:.1f}%" if total_win_rate is not None else "Win Rate: N/A", 
                 cls="text-green-400"),
            ft.P(f"Total Matches: {total_matches}" if total_matches is not None else "Total Matches: N/A", 
                 cls="text-blue-400"),
            ft.P(f"Tournament Wins: {total_tournament_wins}", cls="text-purple-400"),
            ft.P(f"ELO Rating: {total_elo}" if total_elo is not None else "ELO Rating: N/A", 
                 cls="text-yellow-400"),
            ft.P(f"Avg Deck Price: €{mean_price_eur:.2f}" if mean_price_eur is not None else "Avg Deck Price: N/A",
                 cls="text-red-400"),
            cls="space-y-2"
        )
