import json
import html
from fasthtml import ft

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend_fasthtml.components.loading import create_loading_overlay, create_loading_spinner


# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='region'],[name='only_official'],[name='sort_by'],[name='release_meta_formats'],[name='min_matches'],[name='max_matches']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/leaderboard",
    "hx_trigger": "change", 
    "hx_target": "#leaderboard-table",
    "hx_include":HX_INCLUDE,
    "hx_indicator": "#loading-indicator"
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components(max_match_count: int = 10000):
    # Meta format select
    meta_format_select = ft.Select(
        label="Meta Format",
        id="meta-format-select", 
        name="meta_format",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(mf, value=mf, selected=mf == MetaFormat.latest_meta_format) for mf in reversed(MetaFormat.to_list())],
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
        *[ft.Option(r, value=r, selected=(r == MetaFormatRegion.ALL)) for r in regions],
        **FILTER_HX_ATTRS,
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
        ft.Script(src="/public/js/double_range_slider.js"),
        ft.Link(rel="stylesheet", href="/public/css/double_range_slider.css"),
        cls="mb-6"
    )
    
    return ft.Div(
        meta_format_select,
        release_meta_formats_select,
        region_select,
        official_toggle,
        sort_by_select,
        match_count_slider,
        cls="space-y-4"
    )

def create_chart_data_for_leader(leader: LeaderExtended, all_leaders: list[LeaderExtended], meta_format: MetaFormat, last_n: int = 5) -> list[dict]:
    """Create chart data for a specific leader from the already loaded leader data."""
    # Get all meta formats and find the current meta format index
    all_meta_formats = MetaFormat.to_list()
    meta_format_index = all_meta_formats.index(meta_format)
    
    # Get leader history from all_leaders
    leader_history = [l for l in all_leaders if l.id == leader.id and l.only_official == leader.only_official]
    
    # Sort by meta format to ensure chronological order
    leader_history.sort(key=lambda x: all_meta_formats.index(x.meta_format))
    
    # Find the first meta format where this leader has data
    first_meta_format = leader_history[0].meta_format if leader_history else None
    start_index = all_meta_formats.index(first_meta_format) if first_meta_format in all_meta_formats else 0
    meta_formats_between = all_meta_formats[start_index:]
    
    # Create a lookup for existing data points
    meta_to_leader = {l.meta_format: l for l in leader_history}
    
    # Determine range of meta formats to include based on last_n
    end_index = meta_format_index + 1 - start_index  # Exclusive end index
    start_index = max(0, end_index - last_n)  # Take at most last_n meta formats
    relevant_meta_formats = meta_formats_between[start_index:end_index]
    
    # Prepare data for the chart, including null values for missing meta formats
    chart_data = []
    for meta_format in relevant_meta_formats:
        if meta_format in meta_to_leader:
            leader_data = meta_to_leader[meta_format]
            chart_data.append({
                "meta": str(meta_format),
                "winRate": round(leader_data.win_rate * 100, 2) if leader_data.win_rate is not None else None,
                "elo": leader_data.elo,
                "matches": leader_data.total_matches
            })
        else:
            chart_data.append({
                "meta": str(meta_format),
                "winRate": None,
                "elo": None,
                "matches": None
            })
    
    return chart_data

def create_leaderboard_table(filtered_leaders: list[LeaderExtended], all_leaders: list[LeaderExtended], meta_format: MetaFormat):
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
            ft.Th("Elo", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            ft.Th("Performance", cls="px-4 py-2 bg-gray-800 text-white font-semibold"),
            cls=""
        )
    )
    
    # Create table body
    rows = []
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
                    href=f"/leader?lid={leader.id}&meta_format={meta_format}",
                    cls="text-blue-400 hover:text-blue-300"
                ),
                cls="px-4 py-2"
            ),
            ft.Td(leader.id.split("-")[0], cls="px-4 py-2 text-gray-200"),
            ft.Td(str(leader.tournament_wins), cls="px-4 py-2 text-gray-200"),
            ft.Td(str(leader.total_matches) if leader.total_matches is not None else "N/A", cls="px-4 py-2 text-gray-200"),
            ft.Td(f"{leader.win_rate * 100:.2f}%" if leader.win_rate is not None else "N/A", cls="px-4 py-2 text-gray-200"),
            ft.Td(f"{int(leader.d_score * 100)}%" if leader.d_score is not None else "N/A", cls="px-4 py-2 text-gray-200"),
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
                        hx_trigger="load",
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
        # Table
        ft.Table(
            header,
            body,
            cls="min-w-full divide-y divide-gray-700"
        ),
        cls="relative",
        hx_indicator="#leaderboard-loading"
    )
    
    return table_container

def home_page():
    return ft.Div(
        ft.H1("Leaderboard", cls="text-3xl font-bold text-white mb-6"),
        ft.Div(
            ft.Div(
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
        cls="relative"  # Changed from min-h-screen to relative to work with layout
    ) 