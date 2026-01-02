import json
import html
from fasthtml import ft

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend.components.loading import create_loading_overlay, create_loading_spinner
from op_tcg.frontend.components.layout import create_mobile_filter_button


# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='region'],[name='sort_by'],[name='release_meta_formats'],[name='min_matches'],[name='max_matches'],[name='min_price'],[name='max_price']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/leaderboard",
    "hx_trigger": "change", 
    "hx_target": "#leaderboard-table",
    "hx_include":HX_INCLUDE,
    "hx_indicator": "#loading-indicator"
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components(max_match_count: int = 10000, selected_meta_format: MetaFormat | None = None, selected_region: MetaFormatRegion | None = None):
    # Meta format select
    # Determine selected values with fallbacks
    selected_meta_format = selected_meta_format or MetaFormat.latest_meta_format
    selected_region = selected_region or MetaFormatRegion.ALL
    
    meta_format_select = ft.Select(
        label="Meta Format",
        id="meta-format-select", 
        name="meta_format",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(mf, value=mf, selected=mf == selected_meta_format) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS,
    )
    
    # Release meta formats multi-select
    release_meta_formats_select = ft.Select(
        label="Release Meta Formats",
        id="release-meta-formats-select",
        name="release_meta_formats",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS,
    )
    
    # Region select
    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=(r == selected_region)) for r in regions],
        **FILTER_HX_ATTRS,
    )
    
    # Sort by select
    sort_by_select = ft.Select(
        label="Sort By",
        id="sort-by-select",
        name="sort_by",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(opt, value=opt) for opt in LeaderboardSortBy.to_list()],
        **FILTER_HX_ATTRS,
    )
    
    # Match count range slider
    match_count_slider = ft.Div(
        ft.Label("Leader Match Count", cls="text-white font-medium block mb-2"),
        ft.Div(
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(
                    type="range",
                    min="0",
                    max=str(max_match_count),
                    value="0",
                    name="min_matches",
                    cls="slider-range min-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Input(
                    type="range",
                    min="0",
                    max=str(max_match_count),
                    value=str(max_match_count),
                    name="max_matches",
                    cls="slider-range max-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Div(
                    ft.Span("0", cls="min-value text-white"),
                    ft.Span(" - ", cls="text-white mx-2"),
                    ft.Span(str(max_match_count), cls="max-value text-white"),
                    cls="slider-values"
                ),
                cls="double-range-slider",
                id="match-count-slider",
                data_double_range_slider="true"
            ),
            cls="relative w-full"
        ),
        cls="mb-6"
    )

    # Price range slider
    price_slider = ft.Div(
        ft.Label("Avg Deck Price (€)", cls="text-white font-medium block mb-2"),
        ft.Div(
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(
                    type="range",
                    min="0",
                    max="300",
                    value="0",
                    name="min_price",
                    cls="slider-range min-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Input(
                    type="range",
                    min="0",
                    max="300",
                    value="300",
                    name="max_price",
                    cls="slider-range max-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Div(
                    ft.Span("0", cls="min-value text-white"),
                    ft.Span(" - ", cls="text-white mx-2"),
                    ft.Span("300", cls="max-value text-white"),
                    cls="slider-values"
                ),
                cls="double-range-slider",
                id="price-slider",
                data_double_range_slider="true"
            ),
            cls="relative w-full"
        ),
        cls="mb-6"
    )

    return ft.Div(
        meta_format_select,
        region_select,
        release_meta_formats_select,
        sort_by_select,
        match_count_slider,
        price_slider,
        cls="space-y-4"
    )

def create_chart_data_for_leader(leader: LeaderExtended, all_leaders: list[LeaderExtended], meta_format: MetaFormat, last_n: int = 5) -> list[dict]:
    """Create chart data for a specific leader from the already loaded leader data."""
    # Get all meta formats and find the current meta format index
    all_meta_formats = MetaFormat.to_list()
    meta_format_index = all_meta_formats.index(meta_format)
    
    # Get leader history from all_leaders
    leader_history = [l for l in all_leaders if l.id == leader.id and l.only_official == leader.only_official]
    
    # Create a lookup for existing data points
    meta_to_leader = {l.meta_format: l for l in leader_history}
    
    # Determine range of meta formats to include based on last_n
    # We want a fixed window ending at the current meta_format to ensure alignment across all leaders
    end_index = meta_format_index + 1
    start_index = max(0, end_index - last_n)
    relevant_meta_formats = all_meta_formats[start_index:end_index]

    # Prepare data for the chart, including null values for missing meta formats
    chart_data = []
    for mf in relevant_meta_formats:
        if mf in meta_to_leader:
            leader_data = meta_to_leader[mf]
            chart_data.append({
                "meta": str(mf),
                "winRate": round(leader_data.win_rate * 100, 2) if leader_data.win_rate is not None else None,
                "elo": leader_data.elo,
                "matches": leader_data.total_matches
            })
        else:
            chart_data.append({
                "meta": str(mf),
                "winRate": None,
                "elo": None,
                "matches": None
            })
    
    return chart_data

def create_leaderboard_table(filtered_leaders: list[LeaderExtended], all_leaders: list[LeaderExtended], meta_format: MetaFormat, region: MetaFormatRegion | None = None, leader_prices: dict[str, float] | None = None):
    # Filter leaders for the selected meta format
    relevant_meta_formats = MetaFormat.to_list()[:MetaFormat.to_list().index(meta_format) + 1]
    
    # Filter leaders for the selected meta format and relevant meta formats
    selected_meta_leaders = [
        leader for leader in filtered_leaders 
        if leader.meta_format == meta_format and leader.meta_format in relevant_meta_formats
    ]
    
    if not selected_meta_leaders:
        return ft.Div("No leader data available for the selected meta", cls="text-red-400")
    
    # Create table header
    header = ft.Thead(
        ft.Tr(
            ft.Th("Image", cls="px-4 py-2 bg-gray-800 text-white font-semibold w-[200px]"),
            ft.Th("Leader", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Set", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Tournament Wins", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Match Count", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Win Rate", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th(
                ft.Div(
                    ft.Div(
                        "D-Score",
                        ft.Span(
                            "D-Score represents the dominance score of a leader. It takes into account win rate, match count, and tournament performance to provide a comprehensive measure of a leader's strength.",
                            cls="tooltip-text"
                        ),
                        cls="tooltip"
                    ),
                    cls="inline-block"
                ),
                cls="px-4 py-2 bg-gray-800 text-white font-semibold"
            ),
            ft.Th("Avg Price", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Elo", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Win Rate History", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            cls=""
        )
    )
    
    # Create table body
    rows = []
    mobile_cards = []
    # Calculate max_elo only from leaders with elo data
    leaders_with_elo = [leader for leader in selected_meta_leaders if leader.elo is not None]
    max_elo = max(leader.elo for leader in leaders_with_elo) if leaders_with_elo else 0
    
    for idx, leader in enumerate(selected_meta_leaders):
        
        # Calculate color class for Elo
        if leader.elo:
            elo_color_class = "text-green-400" if leader.elo > (max_elo * 0.7) else "text-yellow-400" if leader.elo > (max_elo * 0.4) else "text-red-400"
        else:
            elo_color_class = "text-gray-400"
        
        # Create chart data for this leader
        chart_data = create_chart_data_for_leader(leader, all_leaders, meta_format)
        chart_data_json = json.dumps(chart_data)
        # Escape the JSON for safe HTML attribute usage
        chart_data_escaped = html.escape(chart_data_json)
        
        # Get price
        price = leader_prices.get(leader.id) if leader_prices else None
        price_text = f"€{price:.2f}" if price is not None else "N/A"

        # Mobile Card
        mobile_card = ft.Div(
            ft.Div(
                # Header: Rank and Name
                ft.Div(
                    ft.Span(f"#{idx + 1}", cls="text-xl font-bold text-gray-400 mr-2"),
                    ft.A(
                        leader.name.replace('"', " ").replace('.', " "),
                        href=f"/leader?lid={leader.id}&meta_format={meta_format}{f'&region={region}' if region else ''}",
                        cls="text-lg font-bold text-blue-400 hover:text-blue-300 truncate"
                    ),
                    cls="flex items-center mb-2"
                ),
                # Image and Stats
                ft.Div(
                    # Image
                    ft.Div(
                        cls="w-20 h-20 bg-cover bg-center rounded-lg flex-shrink-0 mr-4",
                        style=f"background-image: url('{leader.aa_image_url}'); border: 2px solid {leader.to_hex_color()};"
                    ),
                    # Stats Grid
                    ft.Div(
                        ft.Div(
                            ft.Span("Win Rate", cls="text-xs text-gray-400 block"),
                            ft.Span(f"{leader.win_rate * 100:.1f}%" if leader.win_rate is not None else "N/A", cls="font-semibold"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("Elo", cls="text-xs text-gray-400 block"),
                            ft.Span(str(leader.elo) if leader.elo is not None else "N/A", cls=f"font-semibold {elo_color_class}"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("Matches", cls="text-xs text-gray-400 block"),
                            ft.Span(str(leader.total_matches) if leader.total_matches is not None else "N/A", cls="font-semibold"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("Top 1", cls="text-xs text-gray-400 block"),
                            ft.Span(str(leader.tournament_wins), cls="font-semibold"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("D-Score", cls="text-xs text-gray-400 block"),
                            ft.Span(f"{int(leader.d_score * 100)}%" if leader.d_score is not None else "N/A", cls="font-semibold"),
                            cls="text-center"
                        ),
                        cls="grid grid-cols-3 gap-2 flex-grow"
                    ),
                    cls="flex"
                ),
                # Footer: Price and Set
                ft.Div(
                    ft.Span(f"Set: {leader.id.split('-')[0]}", cls="text-xs text-gray-500"),
                    ft.Span(price_text, cls="text-xs text-gray-300"),
                    cls="flex justify-between mt-2 pt-2 border-t border-gray-700"
                ),
                # Chart (New)
                ft.Div(
                    # Chart loading indicator
                    create_loading_overlay(
                        id=f"chart-loading-mobile-{leader.id}",
                        size="w-6 h-6"
                    ),
                    # Chart container with embedded chart data
                    ft.Div(
                        id=f"leader-chart-mobile-{leader.id}",
                        hx_post=f"/api/leader-chart/{leader.id}",
                        hx_trigger="intersect once",
                        hx_swap="innerHTML",
                        hx_target=f"#leader-chart-mobile-{leader.id}",
                        hx_include=HX_INCLUDE,
                        hx_indicator=f"#chart-loading-mobile-{leader.id}",
                        hx_vals=f'{{"chart_data": "{chart_data_escaped}"}}',
                        cls="w-full h-[80px]",
                        data_chart_data=chart_data_json
                    ),
                    cls="relative w-full h-[80px] mt-4 border-t border-gray-700 pt-2"
                ),
                cls="bg-gray-800 rounded-lg p-4 shadow-md border border-gray-700 text-left"
            )
        )
        mobile_cards.append(mobile_card)

        cells = [
            ft.Td(
                ft.Div(
                    ft.Div(
                        f"#{idx + 1}",
                        cls="rank-text"
                    ),
                    cls="leaderboard-image-cell",
                    style=f"background-image: linear-gradient(to top, {leader.to_hex_color()}, transparent), url('{leader.aa_image_url}')"

                ),
                cls="p-0"
            ),
            ft.Td(
                ft.A(
                    leader.name.replace('"', " ").replace('.', " "),
                    href=f"/leader?lid={leader.id}&meta_format={meta_format}{f'&region={region}' if region else ''}",
                    cls="text-blue-400 hover:text-blue-300"
                ),
                cls="px-4 py-2"
            ),
            ft.Td(leader.id.split("-")[0], cls="px-4 py-2 text-gray-200"),
            ft.Td(str(leader.tournament_wins), cls="px-4 py-2 text-gray-200"),
            ft.Td(str(leader.total_matches) if leader.total_matches is not None else "N/A", cls="px-4 py-2 text-gray-200"),
            ft.Td(f"{leader.win_rate * 100:.2f}%" if leader.win_rate is not None else "N/A", cls="px-4 py-2 text-gray-200"),
            ft.Td(f"{int(leader.d_score * 100)}%" if leader.d_score is not None else "N/A", cls="px-4 py-2 text-gray-200"),
            ft.Td(price_text, cls="px-4 py-2 text-gray-200"),
            ft.Td(str(leader.elo) if leader.elo is not None else "N/A", cls=f"px-4 py-2 {elo_color_class}"),
            ft.Td(
                ft.Div(
                    # Chart loading indicator
                    create_loading_overlay(
                        id=f"chart-loading-{leader.id}",
                        size="w-8 h-8"
                    ),
                    # Chart container with embedded chart data
                    ft.Div(
                        id=f"leader-chart-{leader.id}",
                        hx_post=f"/api/leader-chart/{leader.id}",
                        hx_trigger="intersect once",
                        hx_swap="innerHTML",
                        hx_target=f"#leader-chart-{leader.id}",
                        hx_include=HX_INCLUDE,
                        hx_indicator=f"#chart-loading-{leader.id}",
                        hx_vals=f'{{"chart_data": "{chart_data_escaped}"}}',
                        cls="w-[200px] h-[120px]",
                        data_chart_data=chart_data_json
                    ),
                    cls="relative w-[200px] h-[120px]"
                ),
                cls="px-0 py-0 min-w-[200px] h-[120px] relative"
            )
        ]
        
        rows.append(ft.Tr(*cells, cls="border-b border-gray-700 hover:bg-gray-800/50"))
    
    body = ft.Tbody(*rows)
    
    # Create table with loading indicator
    table_container = ft.Div(
        # Loading indicator for the entire table
        create_loading_spinner(
            id="leaderboard-loading",
            size="w-12 h-12",
            container_classes="htmx-indicator w-full h-[200px]"
        ),
        # Desktop Table
        ft.Table(
            header,
            body,
            cls="min-w-full divide-y divide-gray-700 hidden md:table"
        ),
        # Mobile Cards
        ft.Div(
            *mobile_cards,
            cls="md:hidden space-y-4 text-left"
        ),
        cls="relative",
        hx_indicator="#leaderboard-loading"
    )
    
    return table_container

def home_page():
    # Add script to persist meta_format and region in URL on changes
    persist_script = ft.Script("""
        function updateHomeURL() {
            const params = new URLSearchParams(window.location.search);
            const mf = document.getElementById('meta-format-select');
            const rg = document.getElementById('region-select');
            if (mf && mf.value) { params.set('meta_format', mf.value); } else { params.delete('meta_format'); }
            if (rg && rg.value) { params.set('region', rg.value); } else { params.delete('region'); }
            const newURL = window.location.pathname + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({}, '', newURL);
        }
        document.addEventListener('change', function(evt) {
            if (evt.target && (evt.target.id === 'meta-format-select' || evt.target.id === 'region-select')) {
                setTimeout(updateHomeURL, 10);
            }
        });
        document.addEventListener('DOMContentLoaded', function(){ setTimeout(updateHomeURL, 50); });
    """)
    
    # CSS for the notification animations and styling
    notification_styles = ft.Style("""
        .no-match-data-notification,
        .proxy-data-notification {
            animation: fadeIn 0.5s ease-in-out;
        }
        
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        
        .no-match-data-notification button:hover {
            transform: translateY(-1px);
            box-shadow: 0 4px 8px rgba(59, 130, 246, 0.3);
        }
        
        /* Add subtle glow effects */
        .no-match-data-notification {
            box-shadow: 0 4px 20px rgba(251, 146, 60, 0.1);
        }
        
        .proxy-data-notification {
            box-shadow: 0 4px 20px rgba(251, 191, 36, 0.15);
        }
    """)
    
    return ft.Div(
        notification_styles,
        ft.H1("Leaderboard", cls="text-3xl font-bold text-white mb-6"),
        ft.Div(
            ft.Div(
                create_mobile_filter_button(),
                # Loading indicator
                create_loading_spinner(
                    id="loading-indicator",
                    size="w-8 h-8",
                    container_classes="min-h-[100px]"
                ),
                # Content
                ft.Div(
                    cls="text-white text-center py-8",
                    hx_get="/api/leaderboard",
                    hx_trigger="load",
                    hx_include=HX_INCLUDE,
                    hx_target="#leaderboard-table",
                    hx_indicator="#loading-indicator",
                    id="leaderboard-table"
                ),
                cls="relative"
            ),
            cls="space-y-4 overflow-x-auto"
        ),
        persist_script,
        cls="relative"  # Changed from min-h-screen to relative to work with layout
    )
