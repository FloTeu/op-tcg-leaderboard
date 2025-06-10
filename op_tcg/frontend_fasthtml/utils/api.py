from starlette.requests import Request
from typing import Dict, Any, List, Union, TypeVar, Tuple

from op_tcg.frontend_fasthtml.api.models import LeaderboardFilter
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended, get_leaders_with_decklist_data
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion

T = TypeVar('T')

def get_effective_meta_format_with_fallback(
    requested_meta_format: MetaFormat,
    data_list: List[Any],
    meta_format_attr: str = "meta_format"
) -> Tuple[MetaFormat, bool]:
    """
    Get effective meta format with automatic fallback to previous meta if no data exists.
    
    Args:
        requested_meta_format: The originally requested meta format
        data_list: List of data objects that have a meta_format attribute
        meta_format_attr: Name of the meta format attribute (default: "meta_format")
        
    Returns:
        Tuple of (effective_meta_format, fallback_used)
    """
    # Check if requested meta format has data
    matching_data = [
        item for item in data_list 
        if getattr(item, meta_format_attr) == requested_meta_format
    ]
    
    if matching_data:
        return requested_meta_format, False
        
    # No data found, try previous meta format
    all_meta_formats = MetaFormat.to_list()
    current_index = all_meta_formats.index(requested_meta_format)
    
    if current_index > 0:
        fallback_meta_format = all_meta_formats[current_index - 1]
        return fallback_meta_format, True
    
    # If we're already at the first meta format, return the requested one anyway
    return requested_meta_format, False


def create_fallback_notification(
    requested_meta_format: MetaFormat,
    effective_meta_format: MetaFormat,
    dropdown_id: str = "meta-format-select"
):
    """
    Create a notification component for meta format fallback.
    
    Args:
        requested_meta_format: The originally requested meta format
        effective_meta_format: The meta format actually being used
        dropdown_id: ID of the dropdown to update (default: "meta-format-select")
        
    Returns:
        FastHTML Div component with notification and JavaScript
    """
    from fasthtml import ft
    
    return ft.Div(
        ft.Div(
            ft.Div(
                ft.I(cls="fas fa-info-circle mr-2"),
                f"No data available for {requested_meta_format}. Showing data for {effective_meta_format} instead.",
                cls="text-blue-300 text-sm flex items-center"
            ),
            cls="bg-blue-900/50 border border-blue-600 rounded-lg p-3 mb-4"
        ),
        # Add script to update the meta format dropdown
        ft.Script(f"""
            // Update the meta format dropdown to reflect the fallback meta format
            const metaFormatSelect = document.getElementById('{dropdown_id}');
            if (metaFormatSelect) {{
                metaFormatSelect.value = '{effective_meta_format}';
                
                // Trigger change event to ensure any listeners are notified
                const event = new Event('change', {{ bubbles: true }});
                metaFormatSelect.dispatchEvent(event);
            }}
        """),
        cls="fallback-notification"
    )


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


def get_filtered_leaders(request: Request, leader_extended_data: list[LeaderExtended] | None = None):
    query_params = LeaderboardFilter(**get_query_params_as_dict(request))
    
    # Get leader extended data
    if leader_extended_data is None:
        leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=query_params.region)
    
    # Filter by meta format first
    meta_format = query_params.meta_format
    leaders_in_meta = [l for l in leader_extended_data if l.meta_format == meta_format]
    
    # Get leaders that have decklist data in this meta format
    leaders_with_decklists = get_leaders_with_decklist_data([meta_format])
    
    # Apply standard filtering
    filtered_leaders = filter_leader_extended(
        leaders=leaders_in_meta,
        only_official=query_params.only_official,
        release_meta_formats=query_params.release_meta_formats,
        match_count_min=query_params.min_matches,
        match_count_max=query_params.max_matches
    )
    
    # Create a set of leader IDs that are already included in filtered_leaders
    already_included_ids = {fl.id for fl in filtered_leaders}
    
    # Add leaders that have decklist data but might not have match data
    # Only include if they are not already in the filtered_leaders set
    additional_leaders = [
        l for l in leaders_in_meta 
        if l.id in leaders_with_decklists and l.id not in already_included_ids
    ]
    
    # Combine both sets of leaders
    all_filtered_leaders = filtered_leaders + additional_leaders
    
    # Final deduplication step: ensure each leader ID appears only once
    # Keep the first occurrence of each leader ID
    unique_leaders = {}
    for leader in all_filtered_leaders:
        if leader.id not in unique_leaders:
            unique_leaders[leader.id] = leader
    
    return list(unique_leaders.values())