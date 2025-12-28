from typing import Dict
from pydantic import BaseModel
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.extract import get_tournament_decklist_data
from op_tcg.frontend.utils.decklist import decklist_data_to_card_ids, tournament_standings2decklist_data
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup

class SimilarLeaderData(BaseModel):
    """Data class for storing similar leader information"""
    similarity_score: float
    cards_intersection: list[str]
    cards_missing: list[str]
    card_id2avg_count_card: Dict[str, float]

def get_most_similar_leader_data(leader_id: str, meta_formats: list[MetaFormat], threshold_occurrence: float = 0.4) -> Dict[str, SimilarLeaderData]:
    """
    Get data about leaders with similar decklists.
    
    Args:
        leader_id: ID of the leader to find similar decklists for
        meta_formats: List of meta formats to consider
        threshold_occurrence: Minimum occurrence threshold for cards to be considered
        
    Returns:
        Dictionary mapping leader IDs to their similarity data
    """
    # Get tournament decklists for the target leader
    target_decklists = get_tournament_decklist_data(meta_formats=meta_formats, leader_ids=[leader_id])
    if not target_decklists:
        return {}
        
    # Convert to decklist data and get card IDs
    cid2cdata_dict = get_card_id_card_data_lookup()
    target_decklist_data = tournament_standings2decklist_data(target_decklists, cid2cdata_dict)
    target_card_ids = decklist_data_to_card_ids(target_decklist_data, 
                                               occurrence_threshold=threshold_occurrence,
                                               exclude_card_ids=[leader_id])
    
    if not target_card_ids:
        return {}
    
    # Get all leaders' decklists from the same meta formats
    all_decklists = get_tournament_decklist_data(meta_formats=meta_formats)
    
    # Group decklists by leader
    leader2decklists = {}
    for decklist in all_decklists:
        if decklist.leader_id == leader_id:
            continue
        if decklist.leader_id not in leader2decklists:
            leader2decklists[decklist.leader_id] = []
        leader2decklists[decklist.leader_id].append(decklist)
    
    # Calculate similarity for each leader
    result = {}
    for other_leader_id, other_decklists in leader2decklists.items():
        # Get card IDs for the other leader
        other_decklist_data = tournament_standings2decklist_data(other_decklists, cid2cdata_dict)
        other_card_ids = decklist_data_to_card_ids(other_decklist_data,
                                                  occurrence_threshold=threshold_occurrence,
                                                  exclude_card_ids=[other_leader_id])
        
        if not other_card_ids:
            continue
            
        # Calculate intersection and missing cards
        cards_intersection = list(set(target_card_ids) & set(other_card_ids))
        cards_missing = list(set(other_card_ids) - set(target_card_ids))
        
        # Calculate similarity score
        similarity_score = len(cards_intersection) / len(target_card_ids)
        
        # Get average card counts
        card_id2avg_count = {}
        for card_id in cards_intersection + cards_missing:
            if card_id in other_decklist_data.card_id2total_count:
                card_id2avg_count[card_id] = other_decklist_data.card_id2total_count[card_id] / other_decklist_data.num_decklists
        
        # Create similarity data
        result[other_leader_id] = SimilarLeaderData(
            similarity_score=similarity_score,
            cards_intersection=cards_intersection,
            cards_missing=cards_missing,
            card_id2avg_count_card=card_id2avg_count
        )
    
    return result 