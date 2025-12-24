from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.cards import CardCurrency, OPTcgLanguage
from op_tcg.frontend.utils.extract import get_leader_data, get_tournament_decklist_data, get_card_id_card_data_lookup, get_leader_extended
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.card_price import get_decklist_price
from op_tcg.frontend.utils.decklist import tournament_standings2decklist_data
from op_tcg.frontend.utils.filter import filter_leader_extended
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.pages.card_movement import (
    CardFrequencyChange,
    create_card_movement_content,
    create_summary_content,
    create_tabs_content
)
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
        
        # Calculate changes - now using absolute percentage point changes
        freq_change = (current_freq - previous_freq) * 100  # Convert to percentage points
        
        # Determine change type
        if previous_freq == 0 and current_freq > 0:
            change_type = "new"
        elif previous_freq > 0 and current_freq == 0:
            change_type = "disappeared"
        elif abs(freq_change) < 5.0:  # Less than 5 percentage points change
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

def setup_api_routes(rt):
    @rt("/api/card-movement-content")
    def get_card_movement_content(request: Request):
        """Return the card movement content for selected leader and meta format"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        return create_card_movement_content(params.leader_id, params.meta_format)
    
    @rt("/api/card-movement-summary")
    def get_card_movement_summary(request: Request):
        """Return the summary content (above tabs)"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        
        # Get previous meta format
        meta_formats_list = MetaFormat.to_list()
        current_meta_index = meta_formats_list.index(params.meta_format)
        previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else params.meta_format
        
        # Get frequency analysis
        analysis = get_card_frequency_analysis(params.leader_id, params.meta_format, previous_meta)
        
        return create_summary_content(params.leader_id, params.meta_format, analysis)
    
    @rt("/api/card-movement-tabs")
    def get_card_movement_tabs(request: Request):
        """Return the tabs content with all data preloaded"""
        params = CardMovementParams(**get_query_params_as_dict(request))
        
        # Get previous meta format
        meta_formats_list = MetaFormat.to_list()
        current_meta_index = meta_formats_list.index(params.meta_format)
        previous_meta = meta_formats_list[current_meta_index - 1] if current_meta_index > 0 else params.meta_format
        
        # Get frequency analysis
        analysis = get_card_frequency_analysis(params.leader_id, params.meta_format, previous_meta)
        
        return create_tabs_content(params.leader_id, params.meta_format, analysis) 