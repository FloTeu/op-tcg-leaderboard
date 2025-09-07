from typing import List, Optional
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.extract import get_tournament_decklist_data

def filter_leader_extended(
    leaders: List[LeaderExtended],
    only_official: bool = True,
    release_meta_formats: Optional[List[str]] = None,
    selected_leader_colors: Optional[List[str]] = None,
    match_count_min: Optional[int] = None,
    match_count_max: Optional[int] = None
) -> List[LeaderExtended]:
    """
    Filter LeaderExtended objects based on various criteria.
    
    Args:
        leaders: List of LeaderExtended objects to filter
        only_official: Whether to only include official matches
        release_meta_formats: List of meta formats to include
        selected_leader_colors: List of leader colors to include
        match_count_min: Minimum number of matches required
        match_count_max: Maximum number of matches allowed
        
    Returns:
        Filtered list of LeaderExtended objects
    """
    def filter_fn(le: LeaderExtended) -> bool:
        # Handle leaders with no match data (only_official is None)
        # Include them as they might have decklist data
        if le.only_official is None:
            keep_le = True  # Include leaders without match data
        else:
            keep_le = le.only_official == only_official
        
        # filter release_meta_formats
        if release_meta_formats:
            keep_le = keep_le and (le.release_meta_format in release_meta_formats)
            
        # filter colors
        if selected_leader_colors:
            keep_le = keep_le and any(lcolor in selected_leader_colors for lcolor in le.colors)
            
        # filter match_count - only apply if leader has match data
        if match_count_min and le.total_matches is not None:
            keep_le = keep_le and (le.total_matches >= match_count_min)
        if match_count_max and le.total_matches is not None:
            keep_le = keep_le and (le.total_matches <= match_count_max)
            
        return keep_le
    
    return list(filter(filter_fn, leaders))


def get_leaders_with_decklist_data(meta_formats: List[MetaFormat]) -> List[str]:
    """
    Get leader IDs that have decklist data in the specified meta formats.
    
    Args:
        meta_formats: List of meta formats to check for decklist data
        
    Returns:
        List of leader IDs that have decklist data
    """
    
    # Get all decklists for the meta formats
    tournament_decklists = get_tournament_decklist_data(meta_formats=meta_formats)
    
    # Get unique leader IDs that have decklist data
    leaders_with_decklists = {td.leader_id for td in tournament_decklists}
    
    return list(leaders_with_decklists) 