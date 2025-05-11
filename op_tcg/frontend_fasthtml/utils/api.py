from starlette.requests import Request
from typing import Dict, Any, List, Union

from op_tcg.frontend_fasthtml.api.models import LeaderboardFilter
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.backend.models.leader import LeaderExtended

def get_query_params_as_dict(request: Request) -> Dict[str, Any]:
    """
    Get query params as a dict.
    If the query parameter appears multiple times (like in a multi-select),
    it will be returned as a list.
    For form checkboxes, values like "on" are kept as strings.
    
    Returns:
        Dict[str, Any]: A dictionary of query parameters.
    """
    query_params_dict = {}
    for key in request.query_params.keys():
        # Get all values for this key
        values = request.query_params.getlist(key)
        
        if len(values) == 0:
            # If no values, skip
            continue
        elif len(values) == 1:
            # If only one value, store it directly (not as a list)
            query_params_dict[key] = values[0]
        else:
            # If multiple values, store as a list
            query_params_dict[key] = values
            
    return query_params_dict


def get_filtered_leaders(request: Request):
    query_params = LeaderboardFilter(**get_query_params_as_dict(request))
    
    # Get leader extended data
    leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=query_params.region)
    
    # Apply filters
    return filter_leader_extended(
        leaders=leader_extended_data,
        only_official=query_params.only_official,
        release_meta_formats=query_params.release_meta_formats,
        match_count_min=query_params.min_matches,
        match_count_max=query_params.max_matches
    )