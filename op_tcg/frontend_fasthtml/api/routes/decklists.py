from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import (
    get_tournament_decklist_data,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.decklist import create_decklist_section, display_decklist
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams
from op_tcg.backend.models.input import MetaFormat

def setup_api_routes(rt):
    @rt("/api/leader-decklist")
    async def get_leader_decklist(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get decklist data
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format, 
            leader_ids=[params.lid]
        )
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Create decklist section
        return create_decklist_section(params.lid, tournament_decklists, card_id2card_data)

    @rt("/api/decklist/tournament-decklist")
    async def get_tournament_decklist(request: Request):
        params_dict = get_query_params_as_dict(request)
        query_params = LeaderDataParams(**params_dict)
        leader_id = query_params.lid
        meta_formats = query_params.meta_format
        tournament_id = params_dict.get("tournament_id")
        player_id = params_dict.get("player_id")

        if not all([leader_id, meta_formats, tournament_id, player_id]):
            return ft.P("Missing required parameters (lid, meta_format, tournament_id, player_id).", cls="text-red-500 p-4")

        try:
            # Re-fetch tournament decklists for the specific leader and meta formats
            all_tournament_decklists_for_leader = get_tournament_decklist_data(meta_formats=meta_formats, leader_ids=[leader_id])

            # Find the specific decklist by tournament_id and player_id
            selected_decklist_obj = next(
                (td for td in all_tournament_decklists_for_leader 
                 if td.tournament_id == tournament_id and td.player_id == player_id),
                None
            )

            card_id2card_data = get_card_id_card_data_lookup()

            if not selected_decklist_obj:
                return ft.P("Decklist not found.", cls="text-red-500 p-4")
            
            # display_decklist expects dict[str, int] (the actual decklist) and leader_id
            return display_decklist(selected_decklist_obj.decklist, card_id2card_data, leader_id)
        except Exception as e:
            # Catch any other unexpected errors during data fetching or processing
            return ft.P(f"An error occurred while fetching the decklist: {e}", cls="text-red-500 p-4") 