from fasthtml import ft
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.components.filters import create_leader_select_component

# Common HTMX attributes for filter components - Updated to include meta_format_region
HX_INCLUDE = "[name='meta_format'],[name='lid'],[name='meta_format_region']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/leader-data",
    "hx_trigger": "change", 
    "hx_target": "#leader-content",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#loading-indicator"
    # Note: URL updates are handled by JavaScript to maintain /leader path
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components(selected_meta_formats=None, selected_leader_id=None, selected_meta_format_region=None):
    """Create filter components for the leader page.
    
    Args:
        selected_meta_formats: Optional list of meta formats to select
        selected_leader_id: Optional leader ID to pre-select
        selected_meta_format_region: Optional meta format region to select
    """
    latest_meta = MetaFormat.latest_meta_format()
    
    # If no selected formats provided, default to latest
    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]
    
    # If no selected region provided, default to ALL
    if not selected_meta_format_region:
        selected_meta_format_region = MetaFormatRegion.ALL
    
    # Meta format select
    meta_format_select = ft.Select(
        label="Meta Format",
        id="release-meta-formats-select",  # Match the ID from multiselect.js initialization
        name="meta_format",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats)) for mf in reversed(MetaFormat.to_list(region=MetaFormatRegion.ASIA))],
        **{
            "hx_get": "/api/leader-select",
            "hx_target": "#leader-select-wrapper",
            "hx_include": HX_INCLUDE,
            "hx_trigger": "change",
            "hx_swap": "innerHTML",
            "hx_params": "*"  # Include all parameters in the request
            # Note: URL updates are handled by JavaScript to maintain /leader path
        }
    )
    
    # Meta format region select
    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        id="meta-format-region-select",
        name="meta_format_region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=(r == selected_meta_format_region)) for r in regions],
        **{
            "hx_get": "/api/leader-select",
            "hx_target": "#leader-select-wrapper",
            "hx_include": HX_INCLUDE,
            "hx_trigger": "change",
            "hx_swap": "innerHTML",
            "hx_params": "*"  # Include all parameters in the request
            # Note: URL updates are handled by JavaScript to maintain /leader path
        }
    )
    
    # Add a hidden div that will trigger the content update
    content_trigger = ft.Div(
        id="content-trigger",
        **FILTER_HX_ATTRS,
        style="display: none;"
    )
    
    # Add JavaScript to trigger the content update after leader select is updated
    # and handle URL updates
    trigger_script = ft.Script("""
        // Function to update URL with current form values
        function updateLeaderURL() {
            const params = new URLSearchParams();
            
            // Get meta format values
            const metaFormatSelect = document.querySelector('[name="meta_format"]');
            if (metaFormatSelect) {
                const selectedOptions = Array.from(metaFormatSelect.selectedOptions);
                selectedOptions.forEach(option => {
                    if (option.value) {
                        params.append('meta_format', option.value);
                    }
                });
            }
            
            // Get leader ID
            const leaderSelect = document.querySelector('[name="lid"]');
            if (leaderSelect && leaderSelect.value) {
                params.set('lid', leaderSelect.value);
            }
            
            // Get meta format region
            const regionSelect = document.querySelector('[name="meta_format_region"]');
            if (regionSelect && regionSelect.value) {
                params.set('meta_format_region', regionSelect.value);
            }
            
            // Only official is default true in API; no UI toggle
            
            // Update URL
            const newURL = '/leader' + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({}, '', newURL);
        }
        
        document.addEventListener('htmx:afterSettle', function(evt) {
            if (evt.target.id === 'leader-select-wrapper') {
                // Small delay to ensure the select element is fully ready
                setTimeout(function() {
                    const leaderSelect = document.querySelector('[name="lid"]');
                    if (leaderSelect && leaderSelect.value) {
                        updateLeaderURL();
                        htmx.trigger('#content-trigger', 'change');
                    }
                }, 50);
            }
            
            // Update URL after content updates
            if (evt.target.id === 'leader-content') {
                updateLeaderURL();
            }
        });
        
        // Handle filter changes
        document.addEventListener('change', function(evt) {
            if (evt.target.matches('[name="meta_format"], [name="meta_format_region"]')) {
                setTimeout(updateLeaderURL, 10);
            }
            
            if (evt.target.matches('[name="lid"]')) {
                setTimeout(updateLeaderURL, 10);
            }
        });
        
        // Also trigger initial load if we have a selected leader
        document.addEventListener('DOMContentLoaded', function() {
            // Small delay to ensure all elements are ready
            setTimeout(function() {
                const leaderSelect = document.querySelector('[name="lid"]');
                if (leaderSelect && leaderSelect.value) {
                    htmx.trigger('#content-trigger', 'change');
                }
                // Update URL on initial load
                updateLeaderURL();
            }, 100);
        });
    """)
    
    # Hidden input for initial leader selection (will be updated by JavaScript)
    initial_leader_input = ft.Input(
        type="hidden",
        name="initial_lid",
        value=selected_leader_id or "",
        id="initial-leader-id"
    ) if selected_leader_id else None
    
    # Prepare HTMX attributes for leader select wrapper (NO hx-vals)
    leader_select_htmx_attrs = {
        "hx_get": "/api/leader-select",
        "hx_trigger": "load",
        "hx_include": HX_INCLUDE + ",[name='initial_lid']",  # Include the initial leader ID input
        "hx_target": "this",
        "hx_swap": "innerHTML",
        "hx_indicator": "#leader-select-loading"
    }
    
    # Leader select wrapper with initial content loaded via HTMX
    leader_select_wrapper = ft.Div(
        # Initial loading spinner
        create_loading_spinner(
            id="leader-select-loading",
            size="w-6 h-6",
            container_classes="min-h-[60px]"
        ),
        # Load the initial component via HTMX
        **leader_select_htmx_attrs,
        id="leader-select-wrapper",
        cls="relative"  # Required for proper styling
    )
    
    # Components to return
    components = [
        meta_format_select,
        region_select,  # Add region select to the filter components
        leader_select_wrapper,
        content_trigger,
        trigger_script
    ]
    
    # Add initial leader input if provided
    if initial_leader_input:
        components.append(initial_leader_input)
    
    return ft.Div(
        *components,
        cls="space-y-4"
    )

def create_tab_view(has_match_data: bool = True):
    """Create a tabbed interface for the leader page content."""
    
    # Tab buttons - only show matchup analysis if there's match data
    tab_buttons = [
        ft.Button(
            "Decklist Analysis",
            cls="tab-button active bg-gray-700 text-white px-4 py-2 rounded-t-lg",
            onclick="switchTab(event, 'decklist-tab')",
            id="decklist-button"
        )
    ]
    
    if has_match_data:
        tab_buttons.append(
            ft.Button(
                "Matchup Analysis",
                cls="tab-button bg-gray-600 text-gray-300 px-4 py-2 rounded-t-lg ml-1",
                onclick="switchTab(event, 'matchup-tab')",
                hx_get="/api/leader-matchups",
                hx_trigger="click once",
                hx_target="#matchup-tab",
                hx_indicator="#matchup-loading-indicator",
                hx_include=HX_INCLUDE,
                id="matchup-button"
            )
        )
    
    tab_buttons.append(
        ft.Button(
            "Tournaments",
            cls="tab-button bg-gray-600 text-gray-300 px-4 py-2 rounded-t-lg ml-1",
            onclick="switchTab(event, 'tournaments-tab')",
            hx_get="/api/leader-tournaments",
            hx_trigger="click once",
            hx_target="#tournaments-tab",
            hx_indicator="#tournament-loading-indicator",
            hx_include=HX_INCLUDE,
            id="tournaments-button"
        )
    )
    
    # Tab content - only include matchup tab if there's match data
    tab_content = [
        # Decklist Analysis Tab (shown by default)
        ft.Div(
            ft.H2("Decklist Analysis", cls="text-2xl font-bold text-white mb-4"),
            
            # Two-column layout for decklist and similar leader
            ft.Div(
                # Left column - Decklist
                ft.Div(
                    # View Tournament Decklists button right below header
                    ft.Div(
                        ft.Button(
                            ft.Span("View Tournament Decklists", cls="mr-2"),
                            ft.I("→", cls="text-lg"),
                            cls="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition-colors",
                            hx_get="/api/decklist-modal",
                            hx_target="body",
                            hx_swap="beforeend",
                            hx_include=HX_INCLUDE
                        ),
                        cls="text-center mb-6"
                    ),
                    create_loading_spinner(
                        id="decklist-loading-indicator",
                        size="w-8 h-8",
                        container_classes="min-h-[100px]"
                    ),
                    ft.Div(
                        hx_get="/api/leader-decklist",
                        hx_trigger="load",
                        hx_include=HX_INCLUDE,
                        hx_target="#leader-decklist-container",
                        hx_indicator="#decklist-loading-indicator",
                        id="leader-decklist-container",
                        cls="min-h-[300px] w-full"
                    ),
                    cls="w-full md:w-1/2 bg-gray-800 rounded-lg shadow-xl"
                ),
                
                # Right column - Similar Leader
                ft.Div(
                    create_loading_spinner(
                        id="similar-loading-indicator",
                        size="w-8 h-8",
                        container_classes="min-h-[100px]"
                    ),
                    ft.Div(
                        hx_get="/api/leader-similar",
                        hx_trigger="load",
                        hx_include=HX_INCLUDE,
                        hx_target="#leader-similar-container",
                        hx_indicator="#similar-loading-indicator",
                        id="leader-similar-container",
                        cls="min-h-[300px] w-full"
                    ),
                    cls="w-full md:w-1/2 md:pl-6"
                ),
                cls="flex flex-col md:flex-row gap-6"
            ),
            cls="tab-pane md:p-6 p-2",
            id="decklist-tab",
            style="display: block;"  # Show this tab by default
        )
    ]
    
    if has_match_data:
        tab_content.append(
            # Matchup Analysis Tab (loaded via HTMX)
            ft.Div(
                create_loading_spinner(
                    id="matchup-loading-indicator",
                    size="w-8 h-8",
                    container_classes="min-h-[100px]"
                ),
                cls="tab-pane p-6",
                id="matchup-tab"
            )
        )
    
    tab_content.append(
        # Tournaments Tab (loaded via HTMX)
        ft.Div(
            create_loading_spinner(
                id="tournament-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]"
            ),
            cls="tab-pane p-6",
            id="tournaments-tab"
        )
    )
    
    return ft.Div(
        # Tab buttons
        ft.Div(
            *tab_buttons,
            cls="flex border-b border-gray-700"
        ),
        
        # Tab content
        ft.Div(
            *tab_content,
            cls="bg-gray-800 rounded-lg shadow-xl w-full mb-6"
        ),
        
        # JavaScript for tab switching
        ft.Script("""
            function switchTab(event, tabId) {
                // Remove active class from all buttons
                document.querySelectorAll('.tab-button').forEach(button => {
                    button.classList.remove('active', 'bg-gray-700');
                    button.classList.add('bg-gray-600', 'text-gray-300');
                });
                
                // Add active class to clicked button
                event.target.classList.remove('bg-gray-600', 'text-gray-300');
                event.target.classList.add('active', 'bg-gray-700', 'text-white');
                
                // Hide all tab content
                document.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.style.display = 'none';
                });
                
                // Show selected tab content
                document.getElementById(tabId).style.display = 'block';
            }
        """),
        
        # CSS for tabs
        ft.Style("""
            .tab-button.active {
                border-bottom: 2px solid #4299e1;
            }
            .tab-pane {
                display: none;
            }
        """),
        
        cls="w-full"
    )

def create_leader_content(leader_id: str, leader_name: str, aa_image_url: str, total_matches: int | None = None):
    """
    Create the content for a leader page.
    
    Args:
        leader_id: The leader's ID
        leader_name: The leader's name
        aa_image_url: URL to the leader's alternative artwork image
        total_matches: Total number of matches (optional, determines if match data is available)
        
    Returns:
        A Div containing the leader page content
    """
    # Check if leader has match data
    has_match_data = total_matches is not None and total_matches > 0
    
    # Create charts section only if there's match data
    charts_section = ft.Div(
        # Win rate chart
        ft.Div(
            ft.H3("Win Rate History", cls="text-xl font-bold text-white mb-4"),
            create_loading_spinner(
                id="win-rate-chart-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]"
            ),
            ft.Div(
                hx_get=f"/api/leader-chart/{leader_id}",
                hx_trigger="load",
                hx_include=HX_INCLUDE,
                hx_target="#win-rate-chart-container",
                hx_indicator="#win-rate-chart-loading-indicator",
                hx_vals=f'{{"last_n": "10", "color": "neutral"}}',
                id="win-rate-chart-container",
                cls="min-h-[150px] flex items-center justify-center w-full"
            ),
            cls="bg-gray-800 rounded-lg p-6 shadow-xl mb-6"
        ),
        
        # Color matchup radar chart
        ft.Div(
            ft.H3("Color Matchups", cls="text-xl font-bold text-white mb-4"),
            create_loading_spinner(
                id="radar-chart-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]"
            ),
            ft.Div(
                hx_get="/api/leader-radar-chart",
                hx_trigger="load",
                hx_include=HX_INCLUDE,
                hx_target="#leader-radar-chart",
                hx_indicator="#radar-chart-loading-indicator",
                hx_vals=f'{{"lid": "{leader_id}"}}',
                id="leader-radar-chart",
                cls="min-h-[300px] flex items-center justify-center w-full"
            ),
            cls="bg-gray-800 rounded-lg p-6 shadow-xl"
        ),
        cls="w-full md:w-3/4 md:pl-6 flex-grow px-4 md:px-0"
    )
    
    return ft.Div(
        # Page title
        ft.H1(f"Leader: {leader_name} ({leader_id})", 
              cls="text-3xl font-bold text-white mb-6 px-4 md:px-0"),
        
        # Main content: single column for mobile, two-column layout for desktop
        ft.Div(
            # First section - Leader image and stats (full width on mobile)
            ft.Div(
                # Leader image
                ft.Div(
                    ft.Img(src=aa_image_url, cls="w-full rounded-lg shadow-lg"),
                    cls="mb-4"
                ),
                
                # Stats section with HTMX
                ft.Div(
                    create_loading_spinner(
                        id="stats-loading-indicator",
                        size="w-8 h-8",
                        container_classes="min-h-[100px]"
                    ),
                    ft.Div(
                        hx_get="/api/leader-stats",
                        hx_trigger="load",
                        hx_include=HX_INCLUDE,
                        hx_target="#leader-stats-container",
                        hx_indicator="#stats-loading-indicator",
                        id="leader-stats-container",
                        cls="space-y-2"
                    ),
                    cls="bg-gray-700 rounded-lg p-4"
                ),
                cls="w-full md:w-1/4 flex-shrink-0 mb-6 px-4 md:px-0"
            ),
            
            # Second section - Charts or message (full width on mobile)
            charts_section,
            
            cls="flex flex-col md:flex-row gap-4"
        ),
        
        # TabView section
        ft.Div(
            create_tab_view(has_match_data),
            cls="px-4 md:px-0 mt-4"
        ),
        id="leader-content-inner"
    )

def leader_page(leader_id: str | None = None, filtered_leader_data: LeaderExtended | None = None, selected_meta_format: list | None = None):
    """
    Display detailed information about a specific leader.
    
    Args:
        leader_id: Optional leader ID to display
        filtered_leader_data: Optional pre-filtered leader data
        selected_meta_format: Optional list of meta formats to select
    """
    
    # If we already have leader data, use it
    if filtered_leader_data:
        leader_data = filtered_leader_data
    else:
        # Set up attributes for HTMX request
        htmx_attrs = {
            "hx_get": "/api/leader-data",
            "hx_trigger": "load",
            "hx_include": HX_INCLUDE,
            "hx_target": "#leader-content-inner",
            "hx_swap": "innerHTML"
            # Note: URL updates are handled by JavaScript to maintain /leader path
        }
        
        # If leader_id is provided directly, add it as a param to ensure
        # it's included even if not present in the form
        if leader_id:
            htmx_attrs["hx_vals"] = f'{{"lid": "{leader_id}"}}'
        
        # Otherwise, create a container that will be populated via HTMX
        return ft.Div(
            # Loading indicator
            create_loading_spinner(
                id="loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]"
            ),
            # Empty container for leader content that will be loaded via HTMX
            ft.Div(
                **htmx_attrs,
                id="leader-content-inner",
                cls="mt-8"
            ),
            cls="min-h-screen p-0 lg:p-8",  # Removed padding for mobile view only
            id="leader-content"
        )
    
    # If leader data isn't available, show error message
    if not leader_data:
        return ft.Div(
            ft.P("No data available for this leader.", cls="text-red-400"),
            cls="min-h-screen p-8",
            id="leader-content"
        )
    
    # Get leader content
    leader_content = create_leader_content(
        leader_id=leader_data.id,
        leader_name=leader_data.name,
        aa_image_url=leader_data.aa_image_url,
        total_matches=leader_data.total_matches
    )
    
    # Return the complete leader page
    return ft.Div(
        # Loading indicator
        create_loading_spinner(
            id="loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),
        # Leader content
        leader_content,
        cls="min-h-screen p-8",
        id="leader-content"
    ) 