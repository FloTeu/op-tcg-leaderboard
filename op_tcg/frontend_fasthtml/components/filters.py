from fasthtml import ft
from typing import List, Optional, Dict, Any
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended, get_leader_win_rate
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_leader_select_component(
    selected_meta_formats: Optional[List[MetaFormat]] = None,
    selected_leader_id: Optional[str] = None,
    only_official: bool = True,
    wrapper_id: str = "leader-select-wrapper",
    select_id: str = "leader-select",
    select_name: str = "lid",
    label: str = "Leader",
    htmx_attrs: Optional[Dict[str, Any]] = None,
    include_label: bool = True,
    auto_select_top: bool = True,
    css_classes: str = SELECT_CLS + " styled-select"
) -> ft.Div:
    """
    Create a reusable leader select component that depends on meta formats.
    
    Args:
        selected_meta_formats: Optional list of meta formats to filter leaders. 
                             If None, uses latest meta format.
        selected_leader_id: Optional leader ID to pre-select
        only_official: Whether to only include official matches (default: True)
        wrapper_id: ID for the wrapper div (default: "leader-select-wrapper")
        select_id: ID for the select element (default: "leader-select")
        select_name: Name attribute for the select element (default: "lid")
        label: Label text for the select (default: "Leader")
        htmx_attrs: Optional HTMX attributes to add to the select element
        include_label: Whether to include the label (default: True)
        auto_select_top: Whether to auto-select the top leader if none selected (default: True)
        css_classes: CSS classes for the select element
        
    Returns:
        A Div containing the leader select component
    """
    # Default to latest meta format if none provided
    if not selected_meta_formats:
        selected_meta_formats = [MetaFormat.latest_meta_format()]
    
    # Get leader data and filter by meta formats and only official matches
    leader_data = get_leader_extended()
    filtered_leaders = filter_leader_extended(
        leaders=[l for l in leader_data if l.meta_format in selected_meta_formats],
        only_official=only_official
    )
    
    # Create unique leader mapping using only the most recent version from selected meta formats
    unique_leaders = {}
    for leader in filtered_leaders:
        if leader.id not in unique_leaders:
            unique_leaders[leader.id] = leader
        else:
            # If we already have this leader, keep the one from the most recent meta format
            existing_meta_idx = MetaFormat.to_list().index(unique_leaders[leader.id].meta_format)
            current_meta_idx = MetaFormat.to_list().index(leader.meta_format)
            if current_meta_idx > existing_meta_idx:
                unique_leaders[leader.id] = leader
    
    # Sort leaders by d_score and elo, handling None values
    def sort_key(leader):
        d_score = leader.d_score if leader.d_score is not None else 0
        elo = leader.elo if leader.elo is not None else 0
        return (-d_score, -elo)
    
    sorted_leaders = sorted(unique_leaders.values(), key=sort_key)
    
    # Check if the selected leader is available in the filtered leaders
    leader_available = selected_leader_id and any(l.id == selected_leader_id for l in sorted_leaders)
    
    # Only auto-select top leader if:
    # 1. auto_select_top is True AND
    # 2. No leader is selected OR the selected leader is not available
    if auto_select_top and (not selected_leader_id or not leader_available) and sorted_leaders:
        selected_leader_id = sorted_leaders[0].id
    elif not leader_available:
        # If the selected leader is not available and auto_select_top is False, clear selection
        selected_leader_id = None
    
    # Create select options
    options = [
        ft.Option(
            f"{l.name} ({l.id})", 
            value=l.id, 
            selected=(l.id == selected_leader_id)
        ) for l in sorted_leaders
    ]
    
    # Build select element attributes
    select_attrs = {
        "id": select_id,
        "name": select_name,
        "cls": css_classes
    }
    
    # Add HTMX attributes if provided
    if htmx_attrs:
        select_attrs.update(htmx_attrs)
    
    # Create the select element
    select_element = ft.Select(*options, **select_attrs)
    
    # Create the component
    components = []
    if include_label:
        components.append(ft.Label(label, cls="text-white font-medium block mb-2"))
    components.append(select_element)
    
    return ft.Div(
        *components,
        id=wrapper_id,
        cls="relative"  # Required for proper styling
    )


def create_leader_multiselect_component(
    selected_meta_formats: Optional[List[MetaFormat]] = None,
    selected_leader_ids: Optional[List[str]] = None,
    only_official: bool = True,
    wrapper_id: str = "leader-multiselect-wrapper",
    select_id: str = "leader-multiselect",
    select_name: str = "leader_ids",
    label: str = "Leaders",
    htmx_attrs: Optional[Dict[str, Any]] = None,
    include_label: bool = True,
    auto_select_top: int = 5,
    css_classes: str = SELECT_CLS + " multiselect",
    use_win_rate_filtering: bool = True
) -> ft.Div:
    """
    Create a reusable leader multi-select component that depends on meta formats.
    
    Args:
        selected_meta_formats: Optional list of meta formats to filter leaders. 
                             If None, uses latest meta format.
        selected_leader_ids: Optional list of leader IDs to pre-select
        only_official: Whether to only include official matches (default: True)
        wrapper_id: ID for the wrapper div (default: "leader-multiselect-wrapper")
        select_id: ID for the select element (default: "leader-multiselect")
        select_name: Name attribute for the select element (default: "leader_ids")
        label: Label text for the select (default: "Leaders")
        htmx_attrs: Optional HTMX attributes to add to the select element
        include_label: Whether to include the label (default: True)
        auto_select_top: Number of top leaders to auto-select if none selected (default: 5, 0 to disable)
        css_classes: CSS classes for the select element
        use_win_rate_filtering: Whether to filter leaders who have matches in win rate data (default: True)
        
    Returns:
        A Div containing the leader multi-select component
    """
    # Default to latest meta format if none provided
    if not selected_meta_formats:
        selected_meta_formats = [MetaFormat.latest_meta_format()]
    
    # Get leader data
    leader_data = get_leader_extended()
    
    if use_win_rate_filtering:
        # Get win rate data to filter leaders who have matches
        win_rate_data = get_leader_win_rate(meta_formats=selected_meta_formats)
        filtered_win_rate_data = [wr for wr in win_rate_data if wr.only_official == only_official]
        leaders_with_matches = {wr.leader_id for wr in filtered_win_rate_data}
        
        # Filter leaders by meta format and those who have matches
        leader_data = [
            l for l in leader_data 
            if l.meta_format in selected_meta_formats and l.id in leaders_with_matches
        ]
    else:
        # Standard filtering using filter_leader_extended
        filtered_leaders = filter_leader_extended(
            leaders=[l for l in leader_data if l.meta_format in selected_meta_formats],
            only_official=only_official
        )
        leader_data = filtered_leaders
    
    # Sort by d_score and get unique leaders
    leader_data.sort(key=lambda x: (x.d_score if x.d_score is not None else 0), reverse=True)
    seen_leader_ids = set()
    unique_leader_data = []
    for leader in leader_data:
        if leader.id not in seen_leader_ids:
            seen_leader_ids.add(leader.id)
            unique_leader_data.append(leader)
    
    # If no selected leaders provided and auto_select_top is enabled, use top N by d_score
    if not selected_leader_ids and auto_select_top > 0 and unique_leader_data:
        selected_leader_ids = [l.id for l in unique_leader_data[:auto_select_top]]
    
    # Ensure selected_leader_ids is not None for comparison
    if selected_leader_ids is None:
        selected_leader_ids = []
    
    # Create select options
    options = [
        ft.Option(
            f"{leader.name} ({leader.get_color_short_name()})", 
            value=leader.id,
            selected=(leader.id in selected_leader_ids)
        ) 
        for leader in unique_leader_data
    ]
    
    # Build select element attributes
    select_attrs = {
        "id": select_id,
        "name": select_name,
        "multiple": True,
        "size": 1,
        "cls": css_classes
    }
    
    # Add HTMX attributes if provided
    if htmx_attrs:
        select_attrs.update(htmx_attrs)
    
    # Create the select element
    select_element = ft.Select(*options, **select_attrs)
    
    # Create the component
    components = []
    if include_label:
        components.append(ft.Label(label, cls="text-white font-medium block mb-2"))
    components.append(select_element)
    
    return ft.Div(
        *components,
        id=wrapper_id,
        cls="relative"  # Required for proper styling
    ) 