from fasthtml import ft
from typing import List, Optional, Dict, Any
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
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