from typing import List, Optional
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat

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
        keep_le = le.only_official == only_official
        
        # filter release_meta_formats
        if release_meta_formats:
            keep_le = keep_le and (le.release_meta_format in release_meta_formats)
            
        # filter colors
        if selected_leader_colors:
            keep_le = keep_le and any(lcolor in selected_leader_colors for lcolor in le.colors)
            
        # filter match_count
        if match_count_min:
            keep_le = keep_le and (le.total_matches >= match_count_min)
        if match_count_max:
            keep_le = keep_le and (le.total_matches <= match_count_max)
            
        return keep_le
    
    return list(filter(filter_fn, leaders)) 