from starlette.requests import Request
from typing import Dict, Any, List

from op_tcg.frontend_fasthtml.api.models import LeaderboardFilter
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended, get_leaders_with_decklist_data
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion

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


def create_no_match_data_notification(
    current_meta_format: MetaFormat,
    leader_data_available: bool = True,
    dropdown_id: str = "meta-format-select"
):
    """
    Create a notification component when leaders exist but have no match data.
    
    Args:
        current_meta_format: The current meta format with no match data
        dropdown_id: ID of the dropdown to update (default: "meta-format-select")
        
    Returns:
        FastHTML Div component with notification and JavaScript
    """
    from fasthtml import ft
    
    # Get the previous meta format that likely has match data
    all_meta_formats = MetaFormat.to_list(region=MetaFormatRegion.ASIA)
    current_index = all_meta_formats.index(current_meta_format)
    previous_meta = all_meta_formats[current_index - 1] if current_index > 0 else None
    if leader_data_available:
        warning_msg = f"Leaders are available for {current_meta_format}, but detailed match data is not yet available."
    else:
        warning_msg = f"No leaders with match data are available for {current_meta_format} yet."
    if previous_meta:
        return ft.Div(
            ft.Div(
                ft.Div(
                    ft.I(cls="fas fa-chart-line mr-3 text-orange-400"),
                    ft.Div(
                        ft.Div(
                            warning_msg,
                            cls="text-white font-medium mb-2"
                        ),
                        ft.Div(
                            "For comprehensive win rates, match statistics, and performance analysis, view ",
                            ft.Button(
                                f"{previous_meta}",
                                cls="bg-blue-600 hover:bg-blue-700 text-white px-3 py-1 rounded-md text-sm font-medium mx-1 transition-colors duration-200",
                                onclick=f"""
                                    const metaSelect = document.getElementById('{dropdown_id}');
                                    if (metaSelect) {{
                                        metaSelect.value = '{previous_meta}';
                                        const event = new Event('change', {{ bubbles: true }});
                                        metaSelect.dispatchEvent(event);
                                    }}
                                """
                            ),
                            " with detailed tournament data.",
                            cls="text-gray-300 text-sm"
                        ),
                        cls="flex-1"
                    ),
                    cls="flex items-start"
                ),
                cls="bg-gradient-to-r from-orange-900/30 to-blue-900/30 border border-orange-500/50 rounded-lg p-4 mb-4 backdrop-blur-sm"
            ),
            cls="no-match-data-notification animate-fade-in"
        )
    
    return None


def create_proxy_data_notification():
    """
    Create a notification component when proxy tournament match data is being used.
    
    Returns:
        FastHTML Div component with notification
    """
    from fasthtml import ft
    
    return ft.Div(
        ft.Div(
            ft.Div(
                ft.I(cls="fas fa-chart-area mr-3 text-yellow-400"),
                ft.Div(
                    ft.Div(
                        "Using proxy tournament data",
                        cls="text-white font-medium mb-2"
                    ),
                    ft.Div(
                        "Match counts are estimated based on tournament wins since detailed match data is not yet available. ",
                        cls="text-gray-300 text-sm"
                    ),
                    cls="flex-1"
                ),
                cls="flex items-start"
            ),
            cls="bg-gradient-to-r from-yellow-900/30 to-amber-900/30 border border-yellow-500/50 rounded-lg p-4 mb-4 backdrop-blur-sm"
        ),
        cls="proxy-data-notification animate-fade-in"
    )


def detect_no_match_data(leaders: List[LeaderExtended]) -> bool:
    """
    Detect if leaders exist but have no meaningful match data.
    If no leaders exist, no match data is available as well.
    
    Args:
        leaders: List of leader data
        
    Returns:
        True if leaders exist but have no match data, False otherwise
    """
    if not leaders:
        return True
    
    # Check if most leaders have no match data (total_matches is None or 0)
    leaders_without_matches = [
        leader for leader in leaders 
        if leader.total_matches is None or leader.total_matches == 0
    ]
    
    # If more than 80% of leaders have no match data, consider it as "no match data available"
    return len(leaders_without_matches) / len(leaders) > 0.85


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
    
    # Apply standard filtering
    filtered_leaders = filter_leader_extended(
        leaders=leaders_in_meta,
        only_official=query_params.only_official,
        release_meta_formats=query_params.release_meta_formats,
        match_count_min=query_params.min_matches,
        match_count_max=query_params.max_matches
    )

    # # Create a set of leader IDs that are already included in filtered_leaders
    # already_included_ids = {fl.id for fl in filtered_leaders}
    #
    # # Get leaders that have decklist data in this meta format
    # leaders_with_decklists = get_leaders_with_decklist_data([meta_format])
    #
    # # Add leaders that have decklist data but might not have match data
    # # Only include if they are not already in the filtered_leaders set
    # additional_leaders = [
    #     l for l in leaders_in_meta
    #     if l.id in leaders_with_decklists and l.id not in already_included_ids
    # ]
    #
    # # Combine both sets of leaders
    # all_filtered_leaders = filtered_leaders + additional_leaders
    #
    # # Final deduplication step: ensure each leader ID appears only once
    # # Keep the first occurrence of each leader ID
    # unique_leaders = {}
    # for leader in all_filtered_leaders:
    #     if leader.id not in unique_leaders:
    #         unique_leaders[leader.id] = leader
    #
    return filtered_leaders #list(unique_leaders.values())