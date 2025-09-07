from datetime import date, datetime
from collections import Counter
from typing import Dict, List, Optional

from pydantic import BaseModel, Field

from op_tcg.backend.models.cards import LatestCardPrice, ExtendedCardData, CardCurrency
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.tournaments import TournamentDecklist
from op_tcg.frontend_fasthtml.utils.extract import get_tournament_decklist_data

class DecklistData(BaseModel):
    num_decklists: int
    avg_price_eur: float | None = None
    avg_price_usd: float | None = None
    card_id2occurrences: dict[str, int]
    card_id2occurrence_proportion: dict[str, float]
    card_id2total_count: dict[str, int]
    card_id2avg_count_card: dict[str, float]
    card_id2card_data: dict[str, LatestCardPrice]
    meta_formats: list[MetaFormat] | None
    min_tournament_date: date | None = None
    max_tournament_date: date | None = None

def tournament_standings2decklist_data(
        tournament_decklists: list[TournamentDecklist],
        card_id2card_data: dict[str, LatestCardPrice]) -> DecklistData:
    """
    Convert tournament decklist data to a decklist data structure
    
    Args:
        tournament_decklists: List of tournament decklists
        card_id2card_data: Mapping of card IDs to card data
    
    Returns:
        DecklistData with aggregated information about the decklists
    """
    num_decklists = len(tournament_decklists)
    card_id2occurrences: dict[str, int] = {}
    card_id2total_count: dict[str, int] = {}
    
    # Count card occurrences and total counts
    for tournament_decklist in tournament_decklists:
        for card_id, count in tournament_decklist.decklist.items():
            if card_id not in card_id2occurrences:
                card_id2occurrences[card_id] = 1
                card_id2total_count[card_id] = count
            else:
                card_id2occurrences[card_id] += 1
                card_id2total_count[card_id] += count
    
    # Calculate averages and proportions
    card_id2avg_count_card = {
        card_id: round(total_count / card_id2occurrences[card_id], 2)
        for card_id, total_count in card_id2total_count.items()
    }
    
    card_id2occurrence_proportion = {
        card_id: occurrences / num_decklists
        for card_id, occurrences in card_id2occurrences.items()
    }
    
    # Get date range
    min_tournament_date = min(td.tournament_timestamp for td in tournament_decklists).date() if tournament_decklists else None
    max_tournament_date = max(td.tournament_timestamp for td in tournament_decklists).date() if tournament_decklists else None
    
    # Get price averages
    avg_price_eur = sum(td.price_eur for td in tournament_decklists if td.price_eur) / num_decklists if tournament_decklists else None
    avg_price_usd = sum(td.price_usd for td in tournament_decklists if td.price_usd) / num_decklists if tournament_decklists else None
    
    # Get meta formats
    meta_formats = list(set(td.meta_format for td in tournament_decklists))
    
    return DecklistData(
        num_decklists=num_decklists,
        avg_price_eur=avg_price_eur,
        avg_price_usd=avg_price_usd,
        card_id2occurrences=card_id2occurrences,
        card_id2occurrence_proportion=card_id2occurrence_proportion,
        card_id2total_count=card_id2total_count,
        card_id2avg_count_card=card_id2avg_count_card,
        card_id2card_data={cid: cdata for cid, cdata in card_id2card_data.items() if cid in card_id2occurrences},
        meta_formats=meta_formats,
        min_tournament_date=min_tournament_date,
        max_tournament_date=max_tournament_date
    )

def decklist_data_to_card_ids(decklist_data: DecklistData, occurrence_threshold: float = 0.0,
                             exclude_card_ids: list[str] | None = None) -> list[str]:
    """
    Get card IDs from decklist data sorted by occurrence
    
    Args:
        decklist_data: Aggregated decklist data
        occurrence_threshold: Minimum occurrence proportion to include a card
        exclude_card_ids: List of card IDs to exclude
    
    Returns:
        List of card IDs sorted by occurrence
    """
    exclude_card_ids = exclude_card_ids or []
    
    # Sort cards by occurrence
    card_ids_sorted = sorted(
        decklist_data.card_id2occurrence_proportion.keys(),
        key=lambda cid: decklist_data.card_id2occurrences[cid], 
        reverse=True
    )
    
    # Filter cards
    return [
        card_id for card_id in card_ids_sorted
        if card_id not in exclude_card_ids and
        decklist_data.card_id2occurrence_proportion[card_id] >= occurrence_threshold
    ]

def get_best_matching_decklist(tournament_decklists: list[TournamentDecklist], 
                              decklist_data: DecklistData) -> dict[str, int]:
    """
    Find the decklist that best matches the aggregated decklist data
    
    Args:
        tournament_decklists: List of tournament decklists
        decklist_data: Aggregated decklist data
    
    Returns:
        The decklist with the highest overlap with the most common cards
    """
    # Get most common cards that would make up a ~50 card deck
    card_ids_sorted = sorted(
        decklist_data.card_id2occurrence_proportion.keys(),
        key=lambda cid: decklist_data.card_id2occurrences[cid], 
        reverse=True
    )
    
    should_have_card_ids = set()
    card_count = 0.0
    
    for card_id in card_ids_sorted:
        if card_count < 51:  # 50 + leader
            should_have_card_ids.add(card_id)
            card_count += decklist_data.card_id2avg_count_card[card_id]
    
    # Find the decklist with the highest overlap
    best_matching_decklist = {}
    best_overlap = 0
    
    for decklist in [td.decklist for td in tournament_decklists]:
        current_overlap = len(set(decklist.keys()).intersection(should_have_card_ids))
        if current_overlap > best_overlap:
            best_matching_decklist = decklist
            best_overlap = current_overlap
    
    return best_matching_decklist

def decklist_to_export_str(decklist: dict[str, int]) -> str:
    """
    Transform a decklist dict into an export string for TCGSim
    
    Args:
        decklist: Dictionary mapping card IDs to counts
    
    Returns:
        String in the format "CountxCardID" for each card
    """
    return "\n".join([f"{count}x{card_id}" for card_id, count in decklist.items()])

def ensure_leader_id(decklist: dict[str, int], leader_id: str) -> dict[str, int]:
    """
    Ensure the leader card is included in the decklist
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        leader_id: Leader card ID
    
    Returns:
        Decklist with leader card included
    """
    return {leader_id: 1, **{k: v for k, v in decklist.items() if k != leader_id}}

def decklist_data_to_fictive_decklist(decklist_data: DecklistData, leader_id: str) -> dict[str, int]:
    """
    Create a representative decklist from aggregated data
    
    Args:
        decklist_data: Aggregated decklist data
        leader_id: Leader card ID
    
    Returns:
        Dictionary mapping card IDs to counts
    """
    decklist = {leader_id: 1}
    total_cards = 1
    
    # Sort cards by occurrence
    sorted_card_ids = decklist_data_to_card_ids(decklist_data, exclude_card_ids=[leader_id])
    
    # Add cards to the decklist
    for card_id in sorted_card_ids:
        if total_cards >= 51:
            break
            
        avg_count = min(4, round(decklist_data.card_id2avg_count_card[card_id]))
        count_to_add = min(avg_count, 51 - total_cards)
        
        if count_to_add > 0:
            decklist[card_id] = count_to_add
            total_cards += count_to_add
    
    return decklist 