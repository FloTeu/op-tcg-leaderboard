from fasthtml import ft
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='leader_id'],[name='only_official']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/leader-data",
    "hx_trigger": "change", 
    "hx_target": "#leader-content",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#loading-indicator"
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components():
    """Create filter components for the leader page."""
    latest_meta = MetaFormat.latest_meta_format
    
    # Meta format select
    meta_format_select = ft.Select(
        label="Meta Format",
        id="release-meta-formats-select",  # Match the ID from multiselect.js initialization
        name="meta_format",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf, selected=(mf == latest_meta)) for mf in reversed(MetaFormat.to_list())],
        **{
            **FILTER_HX_ATTRS,
            "hx_get": "/api/leader-select",
            "hx_target": "#leader-select-wrapper",
            "hx_trigger": "change",
            "hx_swap": "innerHTML"
        }
    )
    
    # Leader select wrapper with initial content
    leader_select_wrapper = ft.Div(
        create_leader_select([latest_meta]),
        id="leader-select-wrapper",
        cls="relative"  # Required for proper styling
    )
    
    # Only official toggle
    official_toggle = ft.Div(
        ft.Label("Only Official Matches", cls="text-white font-medium"),
        ft.Input(
            type="checkbox",
            checked=True,
            id="official-toggle",
            name="only_official",
            **FILTER_HX_ATTRS
        ),
        cls="flex items-center space-x-2"
    )
    
    return ft.Div(
        meta_format_select,
        leader_select_wrapper,
        official_toggle,
        cls="space-y-4"
    )

def create_leader_select(selected_meta_formats=None):
    """Create the leader select component based on selected meta formats."""
    if not selected_meta_formats:
        selected_meta_formats = [MetaFormat.latest_meta_format]
    
    # Get leader data and filter by meta formats and only official matches
    leader_data = get_leader_extended()
    filtered_leaders = filter_leader_extended(
        leaders=[l for l in leader_data if l.meta_format in selected_meta_formats],
        only_official=True
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
    
    # Leader select with sorted options
    return ft.Div(
        ft.Label("Leader", cls="text-white font-medium block mb-2"),
        ft.Select(
            id="leader-select",
            name="leader_id",
            cls=SELECT_CLS + " styled-select",
            *[ft.Option(f"{l.name} ({l.id})", value=l.id) for l in sorted_leaders],
            **{
                **FILTER_HX_ATTRS,
                "hx_push_url": "true"
            }
        ),
        cls="relative"  # Required for proper styling
    )

def get_leader_win_rate_data(leader_data: LeaderExtended) -> list[dict]:
    """Create win rate history data for the chart."""
    # Get all meta formats up to the current one
    all_meta_formats = MetaFormat.to_list()
    current_meta_index = all_meta_formats.index(leader_data.meta_format)
    relevant_meta_formats = all_meta_formats[max(0, current_meta_index - 4):current_meta_index + 1]
    
    # Get leader data for all relevant meta formats
    all_leader_data = get_leader_extended(meta_formats=relevant_meta_formats)
    leader_history = [l for l in all_leader_data if l.id == leader_data.id]
    
    # Create a lookup for existing data points
    meta_to_leader = {l.meta_format: l for l in leader_history}
    
    # Prepare data for the chart, including null values for missing meta formats
    chart_data = []
    for meta_format in relevant_meta_formats:
        if meta_format in meta_to_leader:
            leader = meta_to_leader[meta_format]
            chart_data.append({
                "meta": str(meta_format),
                "winRate": round(leader.win_rate * 100, 2) if leader.win_rate is not None else None
            })
        else:
            chart_data.append({
                "meta": str(meta_format),
                "winRate": None
            })
    
    return chart_data

def leader_page(leader_id: str | None = None, filtered_leader_data: LeaderExtended | None = None):
    """
    Display detailed information about a specific leader.
    If no leader_id is provided, show the leader with the highest d_score.
    """
    # Get leader data if not provided
    leader_data = filtered_leader_data
    if not leader_data:
        if leader_id:
            leader_extended_data = get_leader_extended(leader_ids=[leader_id])
        else:
            # Get all leaders and find the one with highest d_score
            leader_extended_data = get_leader_extended()
            
            # Filter by meta format if specified
            selected_meta_formats = [MetaFormat.latest_meta_format]  # Default to latest
            leader_extended_data = [l for l in leader_extended_data if l.meta_format in selected_meta_formats]
            
            if leader_extended_data:
                # Sort by d_score and elo, handling None values
                def sort_key(leader):
                    d_score = leader.d_score if leader.d_score is not None else 0
                    elo = leader.elo if leader.elo is not None else 0
                    return (-d_score, -elo)
                
                # Create unique leader mapping using only the most recent version from selected meta formats
                unique_leaders = {}
                for leader in leader_extended_data:
                    if leader.id not in unique_leaders:
                        unique_leaders[leader.id] = leader
                    else:
                        # If we already have this leader, keep the one from the most recent meta format
                        existing_meta_idx = MetaFormat.to_list().index(unique_leaders[leader.id].meta_format)
                        current_meta_idx = MetaFormat.to_list().index(leader.meta_format)
                        if current_meta_idx > existing_meta_idx:
                            unique_leaders[leader.id] = leader
                
                sorted_leaders = sorted(unique_leaders.values(), key=sort_key)
                if sorted_leaders:
                    leader_id = sorted_leaders[0].id
        
        if leader_extended_data:
            # Filter for official matches
            filtered_data = filter_leader_extended(leader_extended_data, only_official=True)
            if filtered_data:
                leader_data = next((l for l in filtered_data if l.id == leader_id), None)
    
    if not leader_data:
        return ft.Div(
            ft.P("No data available for this leader.", cls="text-red-400"),
            cls="min-h-screen p-8",
            id="leader-content"
        )
    
    return ft.Div(
        # Loading indicator
        create_loading_spinner(
            id="loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),
        # Content container
        ft.Div(
            # Header section with leader info
            ft.Div(
                ft.Div(
                    # Left column - Leader image and basic stats
                    ft.Div(
                        ft.Img(src=leader_data.aa_image_url, cls="w-full rounded-lg shadow-lg"),
                        ft.Div(
                            ft.H2(leader_data.name, cls="text-2xl font-bold text-white mt-4"),
                            ft.P(f"Set: {leader_data.id}", cls="text-gray-400"),
                            ft.Div(
                                ft.P(f"Win Rate: {leader_data.win_rate * 100:.1f}%" if leader_data.win_rate is not None else "Win Rate: N/A", 
                                     cls="text-green-400"),
                                ft.P(f"Total Matches: {leader_data.total_matches}" if leader_data.total_matches is not None else "Total Matches: N/A", 
                                     cls="text-blue-400"),
                                ft.P(f"Tournament Wins: {leader_data.tournament_wins}", cls="text-purple-400"),
                                ft.P(f"ELO Rating: {leader_data.elo}" if leader_data.elo is not None else "ELO Rating: N/A", 
                                     cls="text-yellow-400"),
                                cls="space-y-2 mt-4"
                            ),
                            cls="mt-4"
                        ),
                        cls="w-1/3"
                    ),
                    # Right column - Win rate chart
                    ft.Div(
                        ft.H3("Win Rate History", cls="text-xl font-bold text-white mb-4"),
                        create_line_chart(
                            container_id=f"win-rate-chart-{leader_id}",
                            data=get_leader_win_rate_data(leader_data),
                            show_x_axis=True,
                            show_y_axis=True
                        ),
                        cls="w-2/3 pl-8"
                    ),
                    cls="flex gap-8"
                ),
                cls="bg-gray-800 rounded-lg p-6 shadow-xl"
            ),
            
            # Tabs section
            ft.Div(
                ft.Div(
                    ft.H3("Recent Tournaments", cls="text-xl font-bold text-white"),
                    ft.P("Coming soon...", cls="text-gray-400 mt-2"),
                    cls="bg-gray-800 rounded-lg p-6 mt-6"
                ),
                ft.Div(
                    ft.H3("Popular Decklists", cls="text-xl font-bold text-white"),
                    ft.P("Coming soon...", cls="text-gray-400 mt-2"),
                    cls="bg-gray-800 rounded-lg p-6 mt-6"
                ),
                ft.Div(
                    ft.H3("Matchup Analysis", cls="text-xl font-bold text-white"),
                    ft.P("Coming soon...", cls="text-gray-400 mt-2"),
                    cls="bg-gray-800 rounded-lg p-6 mt-6"
                ),
                cls="space-y-6"
            ),
            id="leader-content-inner"
        ),
        cls="min-h-screen p-8",
        id="leader-content"
    ) 