from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner, create_loading_overlay

SELECT_CLS = "bg-gray-700 text-white p-2 rounded"
FILTER_HX_ATTRS = {
    "hx_get": "/api/tournament-content",
    "hx_trigger": "change",
    "hx_target": "#tournament-content",
    "hx_include": "[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']"
}

def create_filter_components(selected_meta_formats=None, selected_region: MetaFormatRegion | None = None):
    latest_meta = MetaFormat.latest_meta_format()
    
    # If no selected formats provided, default to latest
    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]
    
    # Default region
    selected_region = selected_region or MetaFormatRegion.ALL

    # Release meta formats multi-select - use region for filtering available formats
    meta_format_select = ft.Select(
        label="Meta Formats",
        id="meta-formats-select",
        name="meta_format",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats)) for mf in reversed(MetaFormat.to_list(region=selected_region))],
        **FILTER_HX_ATTRS
    )

    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=(r == selected_region)) for r in regions],
        **FILTER_HX_ATTRS
    )

    return ft.Div(
        meta_format_select,
        region_select,
        cls="space-y-4"
    )

def create_tournament_content():
    return ft.Div(
        # Header and Filters Section
        ft.Div(
            ft.H1("Tournaments", cls="text-3xl font-bold text-white"),
            cls="mb-8"
        ),

        # Analytics Dashboard Section - Mobile-optimized layout
        ft.Div(
            ft.H2("Tournament Analytics", cls="text-2xl md:text-3xl font-bold text-white mb-6 md:mb-8 text-center px-2"),
            
            # Chart Grid Container - Mobile-first responsive design
            ft.Div(
                # Decklist Popularity Section
                ft.Div(
                    ft.Div(
                        ft.H3("Tournament Decklist Popularity", cls="text-lg md:text-xl font-semibold text-white mb-3 md:mb-4"),
                        # Hidden input to track toggle state (leaders/colors)
                        ft.Input(
                            type="hidden",
                            name="view_mode",
                            value="leaders",
                            id="donut-view-mode"
                        ),
                        ft.Div(
                        ft.Div(
                            ft.Label("Timeframe", cls="text-white font-medium block mb-2 text-sm md:text-base"),
                            ft.Select(
                                ft.Option("Last 7 days", value="7"),
                                ft.Option("Last 14 days", value="14", selected=True),
                                ft.Option("Last 30 days", value="30"),
                                ft.Option("Last 90 days", value="90"),
                                ft.Option("All", value="all"),
                                id="decklist-timeframe-select",
                                name="days",
                                cls=SELECT_CLS + " styled-select w-full text-sm md:text-base",
                                hx_get="/api/tournaments/decklist-donut-smart",
                                hx_trigger="change",
                                hx_target="#tournament-decklist-donut",
                                hx_include="[name='meta_format'],[name='region'],[name='days'],[name='placing'],[name='view_mode']",
                                hx_indicator="#decklist-donut-loading"
                            ),
                            cls="flex-1"
                        ),
                        ft.Div(
                            ft.Label("Tournament Placing", cls="text-white font-medium block mb-2 text-sm md:text-base"),
                            ft.Select(
                                ft.Option("All", value="all", selected=True),
                                ft.Option("Top 1", value="1"),
                                ft.Option("Top 4", value="4"),
                                ft.Option("Top 8", value="8"),
                                id="decklist-placing-select",
                                name="placing",
                                cls=SELECT_CLS + " styled-select w-full text-sm md:text-base",
                                hx_get="/api/tournaments/decklist-donut-smart",
                                hx_trigger="change",
                                hx_target="#tournament-decklist-donut",
                                hx_include="[name='meta_format'],[name='region'],[name='days'],[name='placing'],[name='view_mode']",
                                hx_indicator="#decklist-donut-loading"
                            ),
                            cls="flex-1"
                        ),
                            cls="flex flex-col md:flex-row gap-3 md:gap-4 mb-3 md:mb-4"
                        ),
                        ft.Div(
                            # Toggle: Leader vs Color donut (segmented control)
                            ft.Div(
                                ft.Button(
                                    ft.Span("Leaders", cls="px-3"),
                                    id="donut-toggle-leaders",
                                    cls=(
                                        "inline-flex items-center justify-center text-sm font-medium transition-colors "
                                        "px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 "
                                        "bg-blue-600 text-white shadow-sm"
                                    ),
                                    aria_pressed="true",
                                    hx_get="/api/tournaments/decklist-donut-smart",
                                    hx_trigger="click",
                                    hx_target="#tournament-decklist-donut",
                                    hx_include="[name='meta_format'],[name='region'],[name='days'],[name='placing'],[name='view_mode']",
                                    hx_indicator="#decklist-donut-loading"
                                ),
                                ft.Button(
                                    ft.Span("Colors", cls="px-3"),
                                    id="donut-toggle-colors",
                                    cls=(
                                        "inline-flex items-center justify-center text-sm font-medium transition-colors "
                                        "px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 "
                                        "bg-gray-700 text-gray-200 hover:bg-gray-600"
                                    ),
                                    aria_pressed="false",
                                    hx_get="/api/tournaments/decklist-donut-smart",
                                    hx_trigger="click",
                                    hx_target="#tournament-decklist-donut",
                                    hx_include="[name='meta_format'],[name='region'],[name='days'],[name='placing'],[name='view_mode']",
                                    hx_indicator="#decklist-donut-loading",
                                    style="margin-left:6px;"
                                ),
                                cls=(
                                    "inline-flex items-center p-1 rounded-full bg-gray-700/60 ring-1 ring-white/10 "
                                    "backdrop-blur supports-[backdrop-filter]:bg-gray-700/40 mb-2"
                                ),
                                role="group",
                                aria_label="Donut view mode"
                            ),
                            # Loading overlay positioned absolutely within the chart container
                            create_loading_overlay(
                                id="decklist-donut-loading",
                                size="w-8 h-8"
                            ),
                            ft.Div(
                                id="tournament-decklist-donut",
                                hx_get="/api/tournaments/decklist-donut-smart",
                                hx_trigger="load",
                                hx_include="[name='meta_format'],[name='region'],[name='days'],[name='placing'],[name='view_mode']",
                                hx_indicator="#decklist-donut-loading",
                                cls="w-full h-full"
                            ),
                            # Active state script for the segmented control
                            ft.Script(
                                """
                                (function(){
                                  const leadersBtn = document.getElementById('donut-toggle-leaders');
                                  const colorsBtn = document.getElementById('donut-toggle-colors');
                                  const viewModeInput = document.getElementById('donut-view-mode');
                                  if (!leadersBtn || !colorsBtn || !viewModeInput) return;
                                  
                                  function activate(isLeaders){
                                    // Update hidden input to track current mode
                                    viewModeInput.value = isLeaders ? 'leaders' : 'colors';
                                    
                                    if (isLeaders){
                                      leadersBtn.className = 'inline-flex items-center justify-center text-sm font-medium transition-colors px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 bg-blue-600 text-white shadow-sm';
                                      leadersBtn.setAttribute('aria-pressed','true');
                                      colorsBtn.className = 'inline-flex items-center justify-center text-sm font-medium transition-colors px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 bg-gray-700 text-gray-200 hover:bg-gray-600';
                                      colorsBtn.setAttribute('aria-pressed','false');
                                    } else {
                                      colorsBtn.className = 'inline-flex items-center justify-center text-sm font-medium transition-colors px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 bg-blue-600 text-white shadow-sm';
                                      colorsBtn.setAttribute('aria-pressed','true');
                                      leadersBtn.className = 'inline-flex items-center justify-center text-sm font-medium transition-colors px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 bg-gray-700 text-gray-200 hover:bg-gray-600';
                                      leadersBtn.setAttribute('aria-pressed','false');
                                    }
                                  }
                                  
                                  // Default: leaders
                                  activate(true);
                                  leadersBtn.addEventListener('click', function(){ activate(true); });
                                  colorsBtn.addEventListener('click', function(){ activate(false); });
                                })();
                                """
                            ),
                            cls="relative bg-gray-800/30 rounded-lg p-2 md:p-4 overflow-hidden",
                            style="min-height: 320px; height: 400px; width: 100%;"
                        ),
                        cls="bg-gray-900/50 rounded-xl p-3 md:p-6 backdrop-blur-sm border border-gray-700/30"
                    ),
                    cls="w-full"
                ),
                
                # Tournament Leader Popularity Section
                ft.Div(
                    ft.Div(
                        ft.H3("Tournament Leader Popularity",
                            ft.Span(
                                "ⓘ",
                                cls="ml-2 cursor-help",
                                data_tooltip="Size of the bubbles increases with the tournament wins"
                            ),
                        cls="text-lg md:text-xl font-semibold text-white mb-3 md:mb-6"),
                        ft.Div(
                            # Loading overlay positioned absolutely within the chart container
                            create_loading_overlay(
                                id="tournament-chart-loading",
                                size="w-8 h-8"
                            ),
                            ft.Div(
                                id="tournament-chart-container",
                                hx_get="/api/tournaments/chart",
                                hx_trigger="load",
                                hx_indicator="#tournament-chart-loading",
                                hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
                                cls="w-full h-full"
                            ),
                            cls="relative bg-gray-800/30 rounded-lg p-2 md:p-4 overflow-hidden",
                            style="min-height: 400px; height: auto; width: 100%;"
                        ),
                        # Slider lives outside of the swap target so it isn't replaced on each HTMX response
                        ft.Div(
                            ft.Label("Tournament Match Count Range", cls="text-white font-medium block mb-2"),
                            ft.Div(
                                ft.Div(
                                    ft.Div(cls="slider-track"),
                                    ft.Input(
                                        type="range",
                                        min="0",
                                        max="1000",
                                        value="0",
                                        name="min_matches",
                                        cls="slider-range min-range",
                                        hx_get="/api/tournaments/chart",
                                        hx_trigger="change",
                                        hx_sync="closest .double-range-slider:queue last",
                                        hx_target="#tournament-chart-container",
                                        hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
                                        hx_indicator="#tournament-chart-loading"
                                    ),
                                    ft.Input(
                                        type="range",
                                        min="0",
                                        max="1000",
                                        value="1000",
                                        name="max_matches",
                                        cls="slider-range max-range",
                                        hx_get="/api/tournaments/chart",
                                        hx_trigger="change",
                                        hx_sync="closest .double-range-slider:queue last",
                                        hx_target="#tournament-chart-container",
                                        hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
                                        hx_indicator="#tournament-chart-loading"
                                    ),
                                    ft.Div(
                                        ft.Span("0", cls="min-value text-white"),
                                        ft.Span(" - ", cls="text-white mx-2"),
                                        ft.Span("1000", cls="max-value text-white"),
                                        cls="slider-values"
                                    ),
                                    cls="double-range-slider",
                                    id="tournament-match-slider",
                                    data_double_range_slider="true"
                                ),
                                cls="relative w-full"
                            ),
                            cls="mt-4"
                        ),
                        # Script to hide chart during HTMX request and reveal after single re-create
                        ft.Script("""
                            // Hide chart canvas just before request starts
                            document.addEventListener('htmx:beforeRequest', function(event) {
                                if (event.target && event.target.id === 'tournament-chart-container') {
                                    const canvas = document.getElementById('tournament-chart');
                                    if (canvas) {
                                        canvas.style.visibility = 'hidden';
                                        canvas.style.pointerEvents = 'none';
                                    }
                                }
                            });

                            // Recreate once after swap, then reveal canvas
                            document.addEventListener('htmx:afterSwap', function(event) {
                                if (event.target && event.target.id === 'tournament-chart-container') {
                                    setTimeout(() => {
                                        if (window.recreateBubbleChart) {
                                            window.recreateBubbleChart();
                                        }
                                        const canvas = document.getElementById('tournament-chart');
                                        if (canvas) {
                                            // Reveal on next frame to avoid intermediate draw
                                            requestAnimationFrame(() => {
                                                canvas.style.visibility = 'visible';
                                                canvas.style.pointerEvents = '';
                                            });
                                        }
                                    }, 100);
                                }
                            });
                        """),
                        cls="bg-gray-900/50 rounded-xl p-3 md:p-6 backdrop-blur-sm border border-gray-700/30"
                    ),
                    cls="w-full"
                ),
                
                cls="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 lg:gap-8 w-full"
            ),
            cls="mt-6 md:mt-8 w-full"
        ),
        
        # Tournament List Section
        ft.Div(
            ft.Div(
                ft.H2("Tournament Explorer", cls="text-2xl md:text-3xl font-bold text-white mb-6 md:mb-8 text-center px-2"),
                ft.Div(
                    # Loading overlay positioned absolutely within the list container
                    create_loading_overlay(
                        id="tournament-list-loading",
                        size="w-8 h-8"
                    ),
                    ft.Div(
                        id="tournament-list-container",
                        hx_get="/api/tournaments/all",
                        hx_trigger="load",
                        hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
                        hx_indicator="#tournament-list-loading",
                        cls="w-full h-full"
                    ),
                    cls="relative bg-gray-900/30 rounded-xl p-3 md:p-6 backdrop-blur-sm border border-gray-700/20 overflow-x-auto",
                    style="min-height: 200px;"
                ),
                cls="bg-gradient-to-br from-gray-900/40 to-gray-800/40 rounded-2xl p-4 md:p-8 backdrop-blur-sm border border-gray-600/20"
            ),
            cls="mt-8 md:mt-16"
        ),
        
        cls="min-h-screen p-3 md:p-6 max-w-7xl mx-auto w-full",
        id="tournament-content"
    )

def tournaments_page():
    return ft.Div(
        create_tournament_content()
    ) 