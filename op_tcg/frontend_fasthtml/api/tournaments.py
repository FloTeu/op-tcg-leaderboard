from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import (
    get_tournament_decklist_data,
    get_all_tournament_extened_data,
    get_leader_extended,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.tournament import (
    create_tournament_section,
    create_tournament_keyfacts,
    create_leader_grid
)
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams
from op_tcg.frontend_fasthtml.pages.leader import HX_INCLUDE

def setup_api_routes(rt):
    @rt("/api/leader-tournaments")
    async def get_leader_tournaments(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get tournament data
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            leader_ids=[params.lid]
        )
        tournaments = get_all_tournament_extened_data(meta_formats=params.meta_format)
        
        # Get leader data
        leader_data = get_leader_extended()
        leader_extended_dict = {le.id: le for le in leader_data}
        
        # Get card data
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Create and return the tournament section
        return create_tournament_section(
            leader_id=params.lid,
            tournament_decklists=tournament_decklists,
            tournaments=tournaments,
            leader_extended_dict=leader_extended_dict,
            cid2cdata_dict=card_id2card_data,
            hx_include=HX_INCLUDE
        )

    @rt("/api/tournament-details")
    async def get_tournament_details(request: Request):
        """Get details for a specific tournament."""
        params_dict = get_query_params_as_dict(request)
        tournament_id = params_dict.get("tournament_id")
        params = LeaderDataParams(**params_dict)

        if not tournament_id:
            return ft.P("No tournament selected", cls="text-gray-400")
            
        # Get tournament data
        tournaments = get_all_tournament_extened_data(
            meta_formats=params.meta_format,
        )
        tournament = next((t for t in tournaments if t.id == tournament_id), None)
        
        if not tournament:
            return ft.P("Tournament not found", cls="text-red-400")
            
        # Get card data
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Get tournament decklists
        tournament_decklists = get_tournament_decklist_data(params.meta_format)
        tournament_decklists = [td for td in tournament_decklists if td.tournament_id == tournament_id]
        
        # Get winner info
        winner_card = card_id2card_data.get(params.lid)
        winner_name = f"{winner_card.name} ({params.lid})"
        
        # Calculate leader participation stats
        leader_stats = {}
        if tournament.num_players:
            for lid, placings in tournament.leader_ids_placings.items():
                leader_stats[lid] = len(placings) / tournament.num_players
                
        # Get leader data for images
        leader_data = get_leader_extended()
        leader_extended_dict = {le.id: le for le in leader_data}
        
        # Create the tournament details view
        return ft.Div(
            # Tournament facts
            create_tournament_keyfacts(tournament, winner_name),
            
            # Leader participation section
            ft.Div(
                ft.H4("Leader Participation", cls="text-lg font-bold text-white mb-4"),
                create_leader_grid(leader_stats, leader_extended_dict, card_id2card_data),
                cls="mt-6"
            ),
            
            cls="space-y-6"
        ) 