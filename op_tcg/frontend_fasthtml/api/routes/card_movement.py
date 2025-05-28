from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.cards import CardCurrency, OPTcgLanguage
from op_tcg.frontend_fasthtml.utils.extract import get_leader_data, get_tournament_decklist_data, get_card_id_card_data_lookup, get_leader_extended
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.card_price import get_decklist_price
from op_tcg.frontend_fasthtml.utils.decklist import tournament_standings2decklist_data
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from pydantic import BaseModel, field_validator
from typing import List, Optional
from statistics import mean

class CardMovementParams(BaseModel):
    """Parameters for card movement page requests"""
    meta_format: MetaFormat = MetaFormat.latest_meta_format()
    leader_id: Optional[str] = None
    
    @field_validator('meta_format', mode='before')
    def validate_meta_format(cls, value):
        if isinstance(value, list) and value:
            value = value[0]
        if isinstance(value, str):
            return MetaFormat(value)
        return value

def get_leader_price_data(leader_id: str, current_meta: MetaFormat, previous_meta: MetaFormat):
    """Get price data for a leader across two meta formats"""
    card_id2card_data = get_card_id_card_data_lookup()
    
    # Get tournament decklist data for both meta formats
    current_decklists = get_tournament_decklist_data(
        meta_formats=[current_meta], 
        leader_ids=[leader_id]
    )
    previous_decklists = get_tournament_decklist_data(
        meta_formats=[previous_meta], 
        leader_ids=[leader_id]
    )
    
    # Calculate average prices
    current_price_eur = mean([td.price_eur for td in current_decklists if td.price_eur]) if current_decklists else 0.0
    current_price_usd = mean([td.price_usd for td in current_decklists if td.price_usd]) if current_decklists else 0.0
    previous_price_eur = mean([td.price_eur for td in previous_decklists if td.price_eur]) if previous_decklists else 0.0
    previous_price_usd = mean([td.price_usd for td in previous_decklists if td.price_usd]) if previous_decklists else 0.0
    
    return {
        'current_meta': current_meta,
        'previous_meta': previous_meta,
        'current_price_eur': current_price_eur,
        'current_price_usd': current_price_usd,
        'previous_price_eur': previous_price_eur,
        'previous_price_usd': previous_price_usd,
        'current_decklists_count': len(current_decklists),
        'previous_decklists_count': len(previous_decklists)
    }


def create_card_movement_content(leader_id: str, current_meta: MetaFormat):
    """Create the main content showing leader price comparison with progressive loading"""
    if not leader_id:
        return ft.Div(
            ft.P("Please select a leader to view price movement.", cls="text-gray-300 text-center"),
            cls="text-center py-8"
        )
    
    # Get leader data from extended data (which has d_score and elo)
    leaders = get_leader_extended()
    leader = next((l for l in leaders if l.id == leader_id), None)
    
    if not leader:
        return ft.Div(
            ft.P("Leader not found.", cls="text-red-400 text-center"),
            cls="text-center py-8"
        )
    
    # Get previous meta format based on the current selected meta format
    meta_formats_list = MetaFormat.to_list()
    current_meta_index = meta_formats_list.index(current_meta)
    previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else current_meta
    
    return ft.Div(
        # Leader Image and Basic Info (shown immediately)
        ft.Div(
            ft.Div(
                ft.Img(
                    src=leader.aa_image_url if leader.aa_image_url else leader.image_url,
                    alt=f"{leader.name}",
                    cls="w-full h-auto rounded-lg shadow-lg max-w-sm mx-auto"
                ),
                cls="flex justify-center mb-6"
            ),
            ft.H2(f"{leader.name} ({leader.id})", cls="text-2xl font-bold text-white text-center mb-2"),
            ft.P(f"Life: {leader.life} | Power: {leader.power:,}", cls="text-gray-300 text-center mb-6"),
            cls="mb-8"
        ),
        
        # Price Analysis Section (loaded progressively via HTMX)
        ft.Div(
            ft.H3("Price Movement Analysis", cls="text-xl font-bold text-white mb-6 text-center"),
            
            # Container for price data (will be populated via HTMX)
            ft.Div(
                # Loading indicator for price data (initially visible)
                ft.Div(
                    ft.Div(cls="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"),
                    ft.P("Loading price data...", cls="text-gray-300 text-center mt-4"),
                    cls="flex flex-col items-center justify-center py-12",
                    id="price-loading-indicator"
                ),
                hx_get="/api/card-movement-price-data",
                hx_trigger="load",
                hx_include="[name='meta_format'],[name='leader_id']",
                hx_target="this",
                hx_swap="innerHTML",
                id="price-data-container"
            ),
            
            cls="max-w-4xl mx-auto"
        ),
        
        cls="p-6"
    )

def create_price_data_content(leader_id: str, current_meta: MetaFormat):
    """Create the price data content that loads separately"""
    # Get previous meta format based on the current selected meta format
    meta_formats_list = MetaFormat.to_list()
    current_meta_index = meta_formats_list.index(current_meta)
    previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else current_meta
    
    # Get price data
    price_data = get_leader_price_data(leader_id, current_meta, previous_meta)
    
    # Calculate price changes
    eur_change = price_data['current_price_eur'] - price_data['previous_price_eur']
    usd_change = price_data['current_price_usd'] - price_data['previous_price_usd']
    eur_change_percent = (eur_change / price_data['previous_price_eur'] * 100) if price_data['previous_price_eur'] > 0 else 0
    usd_change_percent = (usd_change / price_data['previous_price_usd'] * 100) if price_data['previous_price_usd'] > 0 else 0
    
    # Determine change colors
    eur_color = "text-green-400" if eur_change >= 0 else "text-red-400"
    usd_color = "text-green-400" if usd_change >= 0 else "text-red-400"
    
    return ft.Div(
        # Current Meta Format Section
        ft.Div(
            ft.H4(f"Current Meta: {current_meta}", cls="text-lg font-semibold text-blue-400 mb-4"),
            ft.Div(
                ft.Div(
                    ft.P("EUR Price", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"€{price_data['current_price_eur']:.2f}", cls="text-2xl font-bold text-white"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                ft.Div(
                    ft.P("USD Price", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"${price_data['current_price_usd']:.2f}", cls="text-2xl font-bold text-white"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                ft.Div(
                    ft.P("Decklists", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"{price_data['current_decklists_count']}", cls="text-2xl font-bold text-white"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                cls="grid grid-cols-3 gap-4 mb-6"
            ),
            cls="mb-8"
        ),
        
        # Previous Meta Format Section
        ft.Div(
            ft.H4(f"Previous Meta: {previous_meta}", cls="text-lg font-semibold text-purple-400 mb-4"),
            ft.Div(
                ft.Div(
                    ft.P("EUR Price", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"€{price_data['previous_price_eur']:.2f}", cls="text-2xl font-bold text-white"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                ft.Div(
                    ft.P("USD Price", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"${price_data['previous_price_usd']:.2f}", cls="text-2xl font-bold text-white"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                ft.Div(
                    ft.P("Decklists", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"{price_data['previous_decklists_count']}", cls="text-2xl font-bold text-white"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                cls="grid grid-cols-3 gap-4 mb-6"
            ),
            cls="mb-8"
        ),
        
        # Price Change Summary
        ft.Div(
            ft.H4("Price Change Summary", cls="text-lg font-semibold text-yellow-400 mb-4"),
            ft.Div(
                ft.Div(
                    ft.P("EUR Change", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"€{eur_change:+.2f}", cls=f"text-xl font-bold {eur_color}"),
                    ft.P(f"({eur_change_percent:+.1f}%)", cls=f"text-sm {eur_color}"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                ft.Div(
                    ft.P("USD Change", cls="text-sm text-gray-400 mb-1"),
                    ft.P(f"${usd_change:+.2f}", cls=f"text-xl font-bold {usd_color}"),
                    ft.P(f"({usd_change_percent:+.1f}%)", cls=f"text-sm {usd_color}"),
                    cls="bg-gray-800 p-4 rounded-lg text-center"
                ),
                cls="grid grid-cols-2 gap-4"
            ),
            cls="mb-8"
        )
    )

def setup_api_routes(rt):
    @rt("/api/card-movement-content")
    def get_card_movement_content(request: Request):
        """Return the card movement content for selected leader and meta format"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        return create_card_movement_content(params.leader_id, params.meta_format)
    
    @rt("/api/card-movement-price-data")
    def get_card_movement_price_data(request: Request):
        """Return the price data content that loads separately"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        return create_price_data_content(params.leader_id, params.meta_format) 