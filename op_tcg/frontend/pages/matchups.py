from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.utils.api import detect_no_match_data
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='leader_ids']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/matchup-content",
    "hx_trigger": "change",
    "hx_target": "#matchup-content",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#matchup-loading-indicator"
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components(selected_meta_formats=None, selected_leader_ids=None, only_official=True):
    """Create filter components for the matchups page using HTMX and API routes.
    
    Args:
        selected_meta_formats: Optional list of meta formats to select
        selected_leader_ids: Optional list of leader IDs to pre-select
        only_official: Whether to filter for official matches only
    """
    leader_extended_data: list[LeaderExtended] = get_leader_extended(
        meta_formats=[MetaFormat.latest_meta_format()])
    contains_no_match_data = detect_no_match_data(leader_extended_data)
    latest_with_match_data = MetaFormatRegion.WEST if contains_no_match_data else MetaFormatRegion.ALL

    latest_meta = MetaFormat.latest_meta_format(region=latest_with_match_data)
    available_meta_formats = MetaFormat.to_list(region=latest_with_match_data)
    
    # If no selected formats provided, default to latest
    if not selected_meta_formats or all(selected_meta_format not in available_meta_formats for selected_meta_format in selected_meta_formats):
        selected_meta_formats = [latest_meta]

    # Meta format multi-select
    meta_format_select = ft.Select(
        label="Meta Formats",
        id="meta-formats-select",
        name="meta_format",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats)) for mf in reversed(available_meta_formats)],
        **{
            "hx_get": "/api/leader-multiselect",
            "hx_target": "#leader-multiselect-wrapper",
            "hx_include": HX_INCLUDE,
            "hx_trigger": "change",
            "hx_swap": "innerHTML",
            "hx_params": "*"  # Include all parameters in the request
        }
    )

    # Only official is default true in API; no UI toggle

    # Add a hidden div that will trigger the content update
    content_trigger = ft.Div(
        id="content-trigger",
        **FILTER_HX_ATTRS,
        style="display: none;"
    )

    # Add JavaScript to trigger the content update after leader select is updated
    trigger_script = ft.Script("""
        document.addEventListener('htmx:afterSettle', function(evt) {
            if (evt.target.id === 'leader-multiselect-wrapper') {
                // Trigger content update after leader multiselect is ready
                htmx.trigger('#content-trigger', 'change');
            }
        });
        
        // Also trigger initial load if we have default leader selections
        document.addEventListener('DOMContentLoaded', function() {
            // Small delay to ensure all elements are ready
            setTimeout(function() {
                const leaderSelect = document.querySelector('[name="leader_ids"]');
                if (leaderSelect && leaderSelect.value) {
                    htmx.trigger('#content-trigger', 'change');
                }
            }, 100);
        });
    """)

    # Leader multiselect wrapper with initial content loaded via HTMX
    leader_multiselect_wrapper = ft.Div(
        # Initial loading spinner
        create_loading_spinner(
            id="leader-multiselect-loading",
            size="w-6 h-6",
            container_classes="min-h-[60px]"
        ),
        # Load the initial component
        hx_get="/api/leader-multiselect",
        hx_trigger="load",
        hx_include=HX_INCLUDE,
        hx_target="this",
        hx_swap="innerHTML",
        hx_indicator="#leader-multiselect-loading",
        id="leader-multiselect-wrapper",
        cls="relative"
    )

    return ft.Div(
        meta_format_select,
        leader_multiselect_wrapper,
        content_trigger,
        trigger_script,
        cls="space-y-4"
    )


def create_matchup_content(selected_meta_formats=None, selected_leader_ids=None, only_official=True):
    """Create the matchup charts and tables content that will be loaded via HTMX."""
    return ft.Div(
        # Matchup Chart Section
        ft.Div(
            ft.H2("Matchup Radar Chart", cls="text-2xl font-bold text-white mb-6"),
            ft.Div(
                # Chart container that loads via HTMX
                ft.Div(
                    id="matchup-chart-container",
                    hx_get="/api/matchups/chart",
                    hx_trigger="load",
                    hx_indicator="#matchup-loading-indicator",
                    hx_include=HX_INCLUDE,
                    cls="w-full min-h-[500px] bg-gray-800 rounded-lg shadow-xl flex items-center justify-center"
                ),
                cls="w-full"
            ),
            cls="mb-8"
        ),
        
        # Matchup Table Section
        ft.Div(
            ft.H2("Matchup Details", cls="text-2xl font-bold text-white mb-6"),
            ft.Div(
                # Table container that loads via HTMX
                ft.Div(
                    id="matchup-table-container",
                    hx_get="/api/matchups/table",
                    hx_trigger="load",
                    hx_indicator="#matchup-loading-indicator",
                    hx_include=HX_INCLUDE,
                    cls="w-full min-h-[300px] bg-gray-800 rounded-lg shadow-xl"
                ),
                cls="w-full overflow-x-auto"
            ),
            cls="w-full"
        ),
        cls="space-y-8"
    )


def matchups_page():
    """Create the main matchups page with HTMX-driven content loading."""
    return ft.Div(
        # Initial content structure (no automatic loading)
        ft.Div(
            # Header Section
            ft.Div(
                ft.H1("Leader Matchups", cls="text-3xl font-bold text-white"),
                ft.P("Analyze matchups between different leaders across meta formats", cls="text-gray-300 mt-2"),
                cls="mb-8"
            ),

            # Loading Spinner for dynamic content
            create_loading_spinner(
                id="matchup-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]"
            ),

            # Content container that will be populated after leader selection
            ft.Div(
                # Initially empty - will be populated via HTMX after leader multiselect is ready
                ft.Div(
                    ft.P("Please select leaders to view matchup analysis", cls="text-gray-400 text-center py-8"),
                    cls="text-center"
                ),
                id="matchup-content",
                cls="w-full"
            ),
            cls="min-h-screen p-4 md:p-6 w-full"
        ),
        cls="w-full"
    ) 