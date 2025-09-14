from datetime import datetime, timezone, timedelta
from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import (
    get_tournament_decklist_data,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.decklist import create_decklist_section
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams
from op_tcg.backend.models.input import MetaFormatRegion
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
            meta_format_region=params.region
        )
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Create decklist section
        return create_decklist_section(params.lid, tournament_decklists, card_id2card_data)

    @rt("/api/decklist-modal")
    async def get_decklist_modal(request: Request):
        """Return the tournament decklist modal content with support for tournament-specific filters."""
        # Parse params using Pydantic model
        params_dict = get_query_params_as_dict(request)
        params = LeaderDataParams(**params_dict)
        
        # Get additional tournament-specific parameters
        days_param = params_dict.get("days", "14")
        placing_param = params_dict.get("placing", "all")
        
        # Get tournament decklist data
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format, 
            leader_ids=[params.lid],
            meta_format_region=params.region
        )
        
        # Apply tournament-specific filters if provided
        if days_param != "all":
            try:
                days = int(days_param)
                since_ts = datetime.now(timezone.utc) - timedelta(days=days)
                tournament_decklists = [d for d in tournament_decklists if d.tournament_timestamp >= since_ts]
            except (TypeError, ValueError):
                # If parsing fails, use all decklists
                pass

        if placing_param != "all":
            try:
                max_placing = int(placing_param)
                tournament_decklists = [d for d in tournament_decklists if d.placing is not None and d.placing <= max_placing]
            except (TypeError, ValueError):
                # If parsing fails, use all decklists
                pass
        
        card_id2card_data = get_card_id_card_data_lookup()
        
        if not tournament_decklists:
            # Create filter description for error message
            filter_desc = []
            if days_param != "all":
                filter_desc.append(f"last {days_param} days")
            if placing_param != "all":
                filter_desc.append(f"Top {placing_param}")
            if params.region != MetaFormatRegion.ALL:
                filter_desc.append(f"region: {params.region.value}")
            
            filter_text = " with filters: " + ", ".join(filter_desc) if filter_desc else ""
            
            return ft.Div(
                ft.Div(
                    ft.Div(
                        ft.Button(
                            ft.I("×", cls="text-3xl leading-none"),
                            cls="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors z-10 w-8 h-8 flex items-center justify-center",
                            onclick="document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove())"
                        ),
                        ft.H2("Tournament Decklists", cls="text-3xl font-bold text-white mb-4"),
                        ft.P(f"No tournament decklist data available for this leader{filter_text}.", cls="text-red-400 text-center p-8"),
                        cls="bg-gray-800 rounded-lg p-6 max-w-4xl w-full mx-4 relative"
                    ),
                    cls="modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 overflow-y-auto py-4",
                    onclick="if (event.target === this) document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove())"
                )
            )
    
        
        # Optional deep-link selection
        selected_tournament_id = params_dict.get("tournament_id")
        selected_player_id = params_dict.get("player_id")
        selected_currency = params_dict.get("currency", "EUR")

        # Create and return the modal - it will handle showing the best ranked decklist by default
        return create_decklist_modal(
            leader_id=params.lid,
            tournament_decklists=tournament_decklists,
            card_id2card_data=card_id2card_data,
            selected_tournament_id=selected_tournament_id,
            selected_player_id=selected_player_id,
            selected_currency=selected_currency,
            days=days_param if days_param != "14" else None,  # Only pass if not default
            placing=placing_param if placing_param != "all" else None  # Only pass if not default
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
        currency = params_dict.get("currency", "EUR")  # Default to EUR
        
        if not tournament_id or not player_id:
            return ft.P("Invalid tournament or player ID", cls="text-red-400")
        
        # Get tournament decklists
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            leader_ids=[params.lid],
            meta_format_region=params.region
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
            display_decklist_modal(selected_decklist, card_id2card_data, params.lid, currency),
            create_decklist_export_component(selected_decklist, params.lid, unique_id),
        ) 