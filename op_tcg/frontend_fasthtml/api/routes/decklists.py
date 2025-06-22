from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import (
    get_tournament_decklist_data,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.decklist import create_decklist_section
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams
from op_tcg.frontend_fasthtml.components.decklist_modal import create_decklist_modal, display_decklist_modal
from op_tcg.frontend_fasthtml.components.decklist_export import create_decklist_export_component

def setup_api_routes(rt):
    @rt("/api/leader-decklist")
    async def get_leader_decklist(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get decklist data
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format, 
            leader_ids=[params.lid],
            meta_format_region=params.meta_format_region
        )
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Create decklist section
        return create_decklist_section(params.lid, tournament_decklists, card_id2card_data)

    @rt("/api/decklist-modal")
    async def get_decklist_modal(request: Request):
        """Return the tournament decklist modal content."""
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get tournament decklist data
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format, 
            leader_ids=[params.lid]
        )
        card_id2card_data = get_card_id_card_data_lookup()
        
        if not tournament_decklists:
            return ft.Div(
                ft.Div(
                    ft.Div(
                        ft.Button(
                            ft.I("×", cls="text-3xl leading-none"),
                            cls="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors z-10 w-8 h-8 flex items-center justify-center",
                            onclick="document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove())"
                        ),
                        ft.H2("Tournament Decklists", cls="text-3xl font-bold text-white mb-4"),
                        ft.P("No tournament decklist data available for this leader.", cls="text-red-400 text-center p-8"),
                        cls="bg-gray-800 rounded-lg p-6 max-w-4xl w-full mx-4 relative"
                    ),
                    cls="modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 overflow-y-auto py-4",
                    onclick="if (event.target === this) document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove())"
                )
            )
        
        # Find the best matching decklist
        from op_tcg.frontend_fasthtml.utils.decklist import (
            tournament_standings2decklist_data, 
            get_best_matching_decklist
        )
        
        decklist_data = tournament_standings2decklist_data(tournament_decklists, card_id2card_data)
        best_matching_decklist_dict = get_best_matching_decklist(tournament_decklists, decklist_data)
        
        # Create and return the modal
        return create_decklist_modal(
            leader_id=params.lid,
            tournament_decklists=tournament_decklists,
            card_id2card_data=card_id2card_data,
            best_matching_decklist=best_matching_decklist_dict
        )
    
    @rt("/api/decklist/tournament-decklist-modal")
    async def get_tournament_decklist_modal(request: Request):
        """Return tournament decklist content for the modal."""
        # Parse params using Pydantic model
        params_dict = get_query_params_as_dict(request)
        params = LeaderDataParams(**params_dict)
        
        # Get tournament and player IDs
        tournament_id = params_dict.get("tournament_id")
        player_id = params_dict.get("player_id")
        
        if not tournament_id or not player_id:
            return ft.P("Invalid tournament or player ID", cls="text-red-400")
        
        # Get tournament decklists
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            leader_ids=[params.lid],
            meta_format_region=params.meta_format_region
        )
        
        # Find the specific decklist
        selected_decklist = None
        for td in tournament_decklists:
            if td.tournament_id == tournament_id and td.player_id == player_id:
                selected_decklist = td.decklist
                break
        
        if not selected_decklist:
            return ft.P("Selected decklist not found", cls="text-red-400")
        
        # Get card data
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Generate unique ID for this specific decklist
        unique_id = f"{tournament_id}-{player_id}".replace(":", "-").replace("/", "-")[:20]
        
        # Return the decklist display with export functionality
        return ft.Div(
            create_decklist_export_component(selected_decklist, params.lid, unique_id),
            display_decklist_modal(selected_decklist, card_id2card_data, params.lid)
        ) 