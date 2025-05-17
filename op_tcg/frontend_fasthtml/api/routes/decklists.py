from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import (
    get_tournament_decklist_data,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.decklist import create_decklist_section
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams

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