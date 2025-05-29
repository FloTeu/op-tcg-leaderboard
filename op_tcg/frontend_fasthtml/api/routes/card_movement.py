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
from typing import List, Optional, Dict, Tuple
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

class CardFrequencyChange(BaseModel):
    """Data class for tracking card frequency changes between meta formats"""
    card_id: str
    card_name: str
    card_image_url: str
    current_frequency: float  # 0.0 to 1.0
    previous_frequency: float  # 0.0 to 1.0
    frequency_change: float  # difference
    frequency_change_percent: float  # percentage change
    current_avg_count: float  # average copies in deck
    previous_avg_count: float  # average copies in deck
    change_type: str  # "increased", "decreased", "new", "disappeared", "stable"

def get_card_frequency_analysis(leader_id: str, current_meta: MetaFormat, previous_meta: MetaFormat) -> Dict:
    """Analyze card frequency changes between two meta formats for a specific leader"""
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
    
    if not current_decklists and not previous_decklists:
        return {"error": "No decklist data found for either meta format"}
    
    # Convert to decklist data structures
    current_data = tournament_standings2decklist_data(current_decklists, card_id2card_data) if current_decklists else None
    previous_data = tournament_standings2decklist_data(previous_decklists, card_id2card_data) if previous_decklists else None
    
    # Get all cards that appear in either meta
    all_card_ids = set()
    if current_data:
        all_card_ids.update(current_data.card_id2occurrence_proportion.keys())
    if previous_data:
        all_card_ids.update(previous_data.card_id2occurrence_proportion.keys())
    
    # Remove leader card from analysis
    all_card_ids.discard(leader_id)
    
    card_changes = []
    for card_id in all_card_ids:
        # Skip if card data not available
        if card_id not in card_id2card_data:
            continue
            
        card_data = card_id2card_data[card_id]
        
        # Get current and previous frequencies
        current_freq = current_data.card_id2occurrence_proportion.get(card_id, 0.0) if current_data else 0.0
        previous_freq = previous_data.card_id2occurrence_proportion.get(card_id, 0.0) if previous_data else 0.0
        
        # Get average counts
        current_avg = current_data.card_id2avg_count_card.get(card_id, 0.0) if current_data else 0.0
        previous_avg = previous_data.card_id2avg_count_card.get(card_id, 0.0) if previous_data else 0.0
        
        # Calculate changes
        freq_change = current_freq - previous_freq
        freq_change_percent = ((current_freq - previous_freq) / previous_freq * 100) if previous_freq > 0 else (100 if current_freq > 0 else 0)
        
        # Determine change type
        if previous_freq == 0 and current_freq > 0:
            change_type = "new"
        elif previous_freq > 0 and current_freq == 0:
            change_type = "disappeared"
        elif abs(freq_change) < 0.05:  # Less than 5% change
            change_type = "stable"
        elif freq_change > 0:
            change_type = "increased"
        else:
            change_type = "decreased"
        
        card_changes.append(CardFrequencyChange(
            card_id=card_id,
            card_name=card_data.name,
            card_image_url=card_data.image_url,
            current_frequency=current_freq,
            previous_frequency=previous_freq,
            frequency_change=freq_change,
            frequency_change_percent=freq_change_percent,
            current_avg_count=current_avg,
            previous_avg_count=previous_avg,
            change_type=change_type
        ))
    
    # Group cards by change type
    increased_cards = [c for c in card_changes if c.change_type == "increased"]
    decreased_cards = [c for c in card_changes if c.change_type == "decreased"]
    new_cards = [c for c in card_changes if c.change_type == "new"]
    disappeared_cards = [c for c in card_changes if c.change_type == "disappeared"]
    stable_cards = [c for c in card_changes if c.change_type == "stable"]
    
    # Sort by frequency change (most significant first)
    increased_cards.sort(key=lambda x: x.frequency_change, reverse=True)
    decreased_cards.sort(key=lambda x: x.frequency_change)  # Most negative first
    new_cards.sort(key=lambda x: x.current_frequency, reverse=True)
    disappeared_cards.sort(key=lambda x: x.previous_frequency, reverse=True)
    stable_cards.sort(key=lambda x: x.current_frequency, reverse=True)
    
    return {
        "current_meta": current_meta,
        "previous_meta": previous_meta,
        "current_decklists_count": len(current_decklists) if current_decklists else 0,
        "previous_decklists_count": len(previous_decklists) if previous_decklists else 0,
        "increased_cards": increased_cards[:20],  # Top 20 increased
        "decreased_cards": decreased_cards[:20],  # Top 20 decreased
        "new_cards": new_cards[:15],  # Top 15 new
        "disappeared_cards": disappeared_cards[:15],  # Top 15 disappeared
        "stable_cards": stable_cards[:10],  # Top 10 stable (high usage)
        "summary": {
            "total_increased": len(increased_cards),
            "total_decreased": len(decreased_cards),
            "total_new": len(new_cards),
            "total_disappeared": len(disappeared_cards),
            "total_stable": len(stable_cards)
        }
    }

def create_card_frequency_section(cards: List[CardFrequencyChange], title: str, color_class: str, 
                                 description: str, current_meta: MetaFormat, show_change: bool = True) -> ft.Div:
    """Create a section showing cards with frequency changes"""
    if not cards:
        return ft.Div(
            ft.H4(f"{title} (0)", cls=f"text-lg font-semibold {color_class} mb-4"),
            ft.P("No cards in this category", cls="text-gray-400 text-center py-4"),
            cls="mb-8"
        )
    
    card_elements = []
    for card in cards:
        # Create change indicator
        if show_change and card.change_type in ["increased", "decreased"]:
            change_text = f"{card.frequency_change_percent:+.1f}%"
            change_color = "text-green-400" if card.frequency_change > 0 else "text-red-400"
        elif card.change_type == "new":
            change_text = "NEW"
            change_color = "text-blue-400"
        elif card.change_type == "disappeared":
            change_text = "GONE"
            change_color = "text-gray-400"
        else:
            change_text = f"{card.current_frequency*100:.1f}%"
            change_color = "text-yellow-400"
        
        card_elements.append(
            ft.Div(
                # Card image with modal trigger
                ft.Div(
                    ft.Img(
                        src=card.card_image_url,
                        alt=card.card_name,
                        cls="w-full h-auto rounded-lg shadow-lg hover:shadow-xl transition-all duration-200 cursor-pointer hover:scale-105",
                        hx_get=f"/api/card-modal?card_id={card.card_id}&meta_format={current_meta}&currency=EUR",
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="relative aspect-[2.5/3.5] overflow-hidden"
                ),
                # Card info
                ft.Div(
                    ft.Div(
                        ft.P(card.card_name[:25] + ("..." if len(card.card_name) > 25 else ""), 
                             cls="font-semibold text-sm text-white text-center"),
                        ft.P(f"Current: {card.current_frequency*100:.1f}%", 
                             cls="text-xs text-gray-300 text-center"),
                        ft.P(f"Previous: {card.previous_frequency*100:.1f}%", 
                             cls="text-xs text-gray-300 text-center") if show_change else None,
                        cls="mb-2"
                    ),
                    ft.Div(
                        ft.Span(change_text, cls=f"text-sm font-bold {change_color}"),
                        cls="text-center"
                    ),
                    cls="mt-2"
                ),
                cls="bg-gray-800 p-3 rounded-lg hover:bg-gray-700 transition-colors duration-200"
            )
        )
    
    return ft.Div(
        ft.H4(f"{title} ({len(cards)})", cls=f"text-lg font-semibold {color_class} mb-4"),
        ft.P(description, cls="text-gray-300 mb-6"),
        ft.Div(
            *card_elements,
            cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-4"
        ),
        cls="mb-12"
    )

def create_card_movement_content(leader_id: str, current_meta: MetaFormat):
    """Create the main content showing leader card frequency analysis"""
    if not leader_id:
        return ft.Div(
            ft.P("Please select a leader to view card movement analysis.", cls="text-gray-300 text-center"),
            cls="text-center py-8"
        )
    
    # Get leader data from extended data
    leaders = get_leader_extended()
    leader = next((l for l in leaders if l.id == leader_id), None)
    
    if not leader:
        return ft.Div(
            ft.P("Leader not found.", cls="text-red-400 text-center"),
            cls="text-center py-8"
        )
    
    # Get previous meta format
    meta_formats_list = MetaFormat.to_list()
    current_meta_index = meta_formats_list.index(current_meta)
    previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else current_meta
    
    return ft.Div(
        # Leader Image and Basic Info
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
            ft.P(f"Life: {leader.life} | Power: {leader.power:,}", cls="text-gray-300 text-center mb-2"),
            ft.P(f"Comparing {previous_meta} → {current_meta}", cls="text-blue-400 text-center mb-6"),
            cls="mb-8"
        ),
        
        # Frequency Analysis Section
        ft.Div(
            ft.H3("Card Play Frequency Analysis", cls="text-xl font-bold text-white mb-6 text-center"),
            ft.P("Track which cards are played more or less often compared to the previous meta format.", 
                 cls="text-gray-300 text-center mb-8"),
            
            # Container for frequency data (will be populated via HTMX)
            ft.Div(
                # Loading indicator
                ft.Div(
                    ft.Div(cls="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-500 mx-auto"),
                    ft.P("Analyzing card frequency changes...", cls="text-gray-300 text-center mt-4"),
                    cls="flex flex-col items-center justify-center py-12",
                    id="frequency-loading-indicator"
                ),
                hx_get="/api/card-movement-frequency-data",
                hx_trigger="load",
                hx_include="[name='meta_format'],[name='leader_id']",
                hx_target="this",
                hx_swap="innerHTML",
                id="frequency-data-container"
            ),
            cls="max-w-7xl mx-auto"
        ),
        cls="p-6"
    )

def create_frequency_data_content(leader_id: str, current_meta: MetaFormat):
    """Create the frequency analysis content that loads separately"""
    # Get previous meta format
    meta_formats_list = MetaFormat.to_list()
    current_meta_index = meta_formats_list.index(current_meta)
    previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else current_meta
    
    # Get frequency analysis
    analysis = get_card_frequency_analysis(leader_id, current_meta, previous_meta)
    
    if "error" in analysis:
        return ft.Div(
            ft.P(analysis["error"], cls="text-red-400 text-center py-8"),
            cls="text-center"
        )
    
    # Create summary stats
    summary_cards = []
    summary_cards.extend([
        ft.Div(
            ft.P("Increased Usage", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_increased']}", cls="text-2xl font-bold text-green-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("Decreased Usage", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_decreased']}", cls="text-2xl font-bold text-red-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("New Cards", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_new']}", cls="text-2xl font-bold text-blue-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P("Disappeared", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['summary']['total_disappeared']}", cls="text-2xl font-bold text-gray-400"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P(f"{current_meta} Decklists", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['current_decklists_count']}", cls="text-2xl font-bold text-white"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        ),
        ft.Div(
            ft.P(f"{previous_meta} Decklists", cls="text-sm text-gray-400 mb-1"),
            ft.P(f"{analysis['previous_decklists_count']}", cls="text-2xl font-bold text-white"),
            cls="bg-gray-800 p-4 rounded-lg text-center"
        )
    ])
    
    return ft.Div(
        # Summary section
        ft.Div(
            ft.H4("Summary", cls="text-lg font-semibold text-yellow-400 mb-4"),
            ft.Div(
                *summary_cards,
                cls="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4"
            ),
            cls="mb-12"
        ),
        
        # Cards with increased usage
        create_card_frequency_section(
            analysis["increased_cards"],
            "📈 Increased Usage",
            "text-green-400",
            "Cards that are played significantly more often in the current meta.",
            current_meta
        ),
        
        # New cards
        create_card_frequency_section(
            analysis["new_cards"], 
            "✨ New Cards",
            "text-blue-400",
            "Cards that appeared in the current meta but weren't played in the previous meta.",
            current_meta,
            show_change=False
        ),
        
        # Cards with decreased usage
        create_card_frequency_section(
            analysis["decreased_cards"],
            "📉 Decreased Usage", 
            "text-red-400",
            "Cards that are played significantly less often in the current meta.",
            current_meta
        ),
        
        # Disappeared cards
        create_card_frequency_section(
            analysis["disappeared_cards"],
            "💀 Disappeared Cards",
            "text-gray-400", 
            "Cards that were played in the previous meta but don't appear in current decklists.",
            current_meta,
            show_change=False
        ),
        
        # Stable high-usage cards
        create_card_frequency_section(
            analysis["stable_cards"],
            "⚖️ Stable Staples",
            "text-yellow-400",
            "Cards with consistently high usage across both metas.",
            current_meta,
            show_change=False
        )
    )

def setup_api_routes(rt):
    @rt("/api/card-movement-content")
    def get_card_movement_content(request: Request):
        """Return the card movement content for selected leader and meta format"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        return create_card_movement_content(params.leader_id, params.meta_format)
    
    @rt("/api/card-movement-frequency-data")
    def get_card_movement_frequency_data(request: Request):
        """Return the frequency analysis content that loads separately"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        return create_frequency_data_content(params.leader_id, params.meta_format) 