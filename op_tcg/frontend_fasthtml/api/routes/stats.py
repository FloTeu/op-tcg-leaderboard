from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams

def setup_api_routes(rt):
    @rt("/api/leader-stats")
    async def get_leader_stats(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get leader data
        leader_data_list = get_leader_extended(meta_formats=params.meta_format, leader_ids=[params.lid])
        
        # filter list by official
        leader_data_list = [ld for ld in leader_data_list if ld.only_official == params.only_official]

        if not leader_data_list:
            return ft.P("No stats available for this leader.", cls="text-red-400")
            
        # Create and return the stats component
        if not leader_data_list:
            return ft.P("No stats available for this leader.", cls="text-red-400")
        
        # Calculate means
        total_win_rate = sum(ld.win_rate for ld in leader_data_list if ld.win_rate is not None) / len(leader_data_list)
        total_matches = sum(ld.total_matches for ld in leader_data_list if ld.total_matches is not None)
        total_tournament_wins = sum(ld.tournament_wins for ld in leader_data_list)
        total_elo = int(sum(ld.elo for ld in leader_data_list if ld.elo is not None) / len(leader_data_list))

        return ft.Div(
            ft.P(f"Win Rate: {total_win_rate * 100:.1f}%" if total_win_rate is not None else "Win Rate: N/A", 
                 cls="text-green-400"),
            ft.P(f"Total Matches: {total_matches}" if total_matches is not None else "Total Matches: N/A", 
                 cls="text-blue-400"),
            ft.P(f"Tournament Wins: {total_tournament_wins}", cls="text-purple-400"),
            ft.P(f"ELO Rating: {total_elo}" if total_elo is not None else "ELO Rating: N/A", 
                 cls="text-yellow-400"),
            cls="space-y-2"
        ) 