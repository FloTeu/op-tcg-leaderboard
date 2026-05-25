import json
import html
from fasthtml import ft

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend.components.loading import create_loading_overlay, create_loading_spinner
from op_tcg.frontend.components.layout import create_mobile_filter_button


def _styles() -> ft.Style:
    return ft.Style("""
.hp-page { font-family: 'Barlow', sans-serif; }

/* Prevent image cell from overflowing its column */
.leaderboard-image-cell { max-width: 100% !important; width: 100% !important; }

/* Tooltip anchored to the right (for columns near right edge) */
.tooltip.hp-tooltip-right .tooltip-text {
    right: 0;
    left: auto;
    transform: none;
    white-space: normal;
    word-wrap: break-word;
    width: 260px;
}
.tooltip.hp-tooltip-right .tooltip-text::after {
    left: auto;
    right: 24px;
    margin-left: 0;
}

.hp-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
}

.hp-section-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.12em;
    color: #475569;
    font-size: 0.75rem;
    text-transform: uppercase;
    margin-bottom: 6px;
    display: block;
}

.hp-select {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.hp-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }

/* Table */
.hp-th {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    font-size: 0.9rem;
    color: #475569;
    background: #0d1424;
    padding: 8px 10px;
    border-bottom: 1px solid #1a2540;
    text-align: left;
}
.hp-th-active { color: #f1f5f9; }
.hp-th-sort { cursor: pointer; transition: color 0.12s; }
.hp-th-sort:hover { color: #94a3b8; }

.hp-tr { border-bottom: 1px solid #1a2540; transition: background 0.1s; }
.hp-tr:hover { background: rgba(56,189,248,0.04); }

.hp-td {
    font-family: 'Barlow', sans-serif;
    font-size: 1rem;
    color: #94a3b8;
    padding: 6px 10px;
    vertical-align: middle;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.hp-td-mono {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.9rem;
    color: #94a3b8;
    padding: 6px 10px;
    vertical-align: middle;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
}

.hp-leader-link {
    font-family: 'Barlow', sans-serif;
    font-weight: 600;
    font-size: 1rem;
    color: #38bdf8;
    text-decoration: none;
    transition: color 0.12s;
    display: block;
    white-space: normal;
    text-align: center;
    line-height: 1.3;
}
.hp-leader-link:hover { color: #7dd3fc; }

/* Slider overrides */
.slider-values {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.85rem;
    color: #38bdf8;
}

/* Notification animations */
.no-match-data-notification,
.proxy-data-notification {
    animation: hp-fade-in 0.4s ease both;
}
@keyframes hp-fade-in {
    from { opacity: 0; transform: translateY(-8px); }
    to   { opacity: 1; transform: translateY(0); }
}
.no-match-data-notification {
    box-shadow: 0 4px 20px rgba(245,158,11,0.12);
}
.proxy-data-notification {
    box-shadow: 0 4px 20px rgba(245,158,11,0.15);
}
""")


def _sort_header(label, column: LeaderboardSortBy, sort_by: LeaderboardSortBy, ascending: bool, hx_include: str, extra_content=None):
    """Render a clickable sort header that triggers an HTMX leaderboard refresh."""
    is_active = sort_by == column
    if is_active:
        icon = "fa-sort-up" if ascending else "fa-sort-down"
        new_ascending = not ascending
    else:
        icon = "fa-sort opacity-50"
        new_ascending = False
    hx_vals = f'{{"sort_by": "{column}", "ascending": "{str(new_ascending).lower()}"}}'
    cls = "flex items-center gap-1 hp-th-sort " + ("hp-th-active" if is_active else "")
    children = (extra_content or ft.Span(label), ft.I(cls=f"fas {icon} ml-1"))
    return ft.Div(
        *children,
        hx_get="/api/leaderboard",
        hx_target="#leaderboard-table",
        hx_include=hx_include,
        hx_vals=hx_vals,
        hx_indicator="#loading-indicator",
        cls=cls,
    )


# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='region'],[name='sort_by'],[name='release_meta_formats'],[name='min_matches'],[name='max_matches'],[name='min_price'],[name='max_price']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/leaderboard",
    "hx_trigger": "change",
    "hx_target": "#leaderboard-table",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#loading-indicator"
}


def _labeled_select(label, select_el):
    return ft.Div(ft.Span(label, cls="hp-section-label"), select_el)


def create_filter_components(max_match_count: int = 10000, selected_meta_format: MetaFormat | None = None, selected_region: MetaFormatRegion | None = None):
    selected_meta_format = selected_meta_format or MetaFormat.latest_meta_format
    selected_region = selected_region or MetaFormatRegion.ALL

    meta_format_select = _labeled_select("Meta Format", ft.Select(
        id="meta-format-select",
        name="meta_format",
        cls="hp-select styled-select",
        *[ft.Option(mf, value=mf, selected=mf == selected_meta_format) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS,
    ))

    release_meta_formats_select = _labeled_select("Release Format", ft.Select(
        id="release-meta-formats-select",
        name="release_meta_formats",
        multiple=True,
        size=1,
        cls="hp-select multiselect",
        *[ft.Option(mf, value=mf) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS,
    ))

    region_select = _labeled_select("Region", ft.Select(
        id="region-select",
        name="region",
        cls="hp-select styled-select",
        *[ft.Option(r, value=r, selected=(r == selected_region)) for r in MetaFormatRegion.to_list()],
        **FILTER_HX_ATTRS,
    ))

    sort_by_select = _labeled_select("Sort By", ft.Select(
        id="sort-by-select",
        name="sort_by",
        cls="hp-select styled-select",
        *[ft.Option(opt, value=opt) for opt in LeaderboardSortBy.to_list()],
        **FILTER_HX_ATTRS,
    ))

    def _slider(label, slider_id, name_min, name_max, val_max):
        return ft.Div(
            ft.Span(label, cls="hp-section-label"),
            ft.Div(
                ft.Div(
                    ft.Div(cls="slider-track"),
                    ft.Input(type="range", min="0", max=str(val_max), value="0",
                             name=name_min, cls="slider-range min-range", **FILTER_HX_ATTRS),
                    ft.Input(type="range", min="0", max=str(val_max), value=str(val_max),
                             name=name_max, cls="slider-range max-range", **FILTER_HX_ATTRS),
                    ft.Div(
                        ft.Span("0", cls="min-value"),
                        ft.Span(" – ", style="color:#475569;"),
                        ft.Span(str(val_max), cls="max-value"),
                        cls="slider-values",
                    ),
                    cls="double-range-slider",
                    id=slider_id,
                    data_double_range_slider="true"
                ),
                cls="relative w-full"
            ),
        )

    return ft.Div(
        meta_format_select,
        region_select,
        release_meta_formats_select,
        sort_by_select,
        _slider("Leader Match Count", "match-count-slider", "min_matches", "max_matches", max_match_count),
        _slider("Avg Deck Price (€)", "price-slider", "min_price", "max_price", 300),
        cls="space-y-4"
    )


def create_chart_data_for_leader(leader: LeaderExtended, all_leaders: list[LeaderExtended], meta_format: MetaFormat, last_n: int = 5) -> list[dict]:
    """Create chart data for a specific leader from the already loaded leader data."""
    all_meta_formats = MetaFormat.to_list()
    meta_format_index = all_meta_formats.index(meta_format)

    leader_history = [l for l in all_leaders if l.id == leader.id and l.only_official == leader.only_official]
    meta_to_leader = {l.meta_format: l for l in leader_history}

    end_index = meta_format_index + 1
    start_index = max(0, end_index - last_n)
    relevant_meta_formats = all_meta_formats[start_index:end_index]

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
            chart_data.append({"meta": str(mf), "winRate": None, "elo": None, "matches": None})

    return chart_data


def create_leaderboard_table(filtered_leaders: list[LeaderExtended], all_leaders: list[LeaderExtended], meta_format: MetaFormat, region: MetaFormatRegion | None = None, leader_prices: dict[str, float] | None = None, sort_by: LeaderboardSortBy = LeaderboardSortBy.WIN_RATE, ascending: bool = False):
    relevant_meta_formats = MetaFormat.to_list()[:MetaFormat.to_list().index(meta_format) + 1]
    selected_meta_leaders = [
        leader for leader in filtered_leaders
        if leader.meta_format == meta_format and leader.meta_format in relevant_meta_formats
    ]

    if not selected_meta_leaders:
        return ft.Div("No leader data available for the selected meta",
                      style="color:#ef4444; font-family:'Barlow',sans-serif;")

    def sh(label, column, extra_content=None):
        return ft.Th(
            _sort_header(label, column, sort_by, ascending, HX_INCLUDE, extra_content=extra_content),
            cls="hp-th",
        )

    dscore_label = ft.Div(
        ft.Div(
            "D-Score",
            ft.Span(
                "D-Score represents the dominance score of a leader. It takes into account win rate, match count, and tournament performance to provide a comprehensive measure of a leader's strength.",
                cls="tooltip-text"
            ),
            cls="tooltip hp-tooltip-right",
        ),
        cls="inline-block"
    )

    header = ft.Thead(
        ft.Tr(
            ft.Th("", cls="hp-th", style="width:200px;"),
            ft.Th("Leader", cls="hp-th", style="text-align:center;"),
            ft.Th("Set", cls="hp-th"),
            sh("Tournament Wins", LeaderboardSortBy.TOURNAMENT_WINS),
            sh("Match Count", LeaderboardSortBy.MATCH_COUNT),
            sh("Win Rate", LeaderboardSortBy.WIN_RATE),
            sh("D-Score", LeaderboardSortBy.DOMINANCE_SCORE, extra_content=dscore_label),
            sh("Avg Price", LeaderboardSortBy.PRICE),
            sh("Elo", LeaderboardSortBy.ELO),
            ft.Th("Win Rate History", cls="hp-th", style="width:160px;"),
        )
    )

    rows = []
    mobile_cards = []
    leaders_with_elo = [l for l in selected_meta_leaders if l.elo is not None]
    max_elo = max(l.elo for l in leaders_with_elo) if leaders_with_elo else 0

    for idx, leader in enumerate(selected_meta_leaders):
        if leader.elo:
            elo_color = "#10b981" if leader.elo > (max_elo * 0.7) else "#f59e0b" if leader.elo > (max_elo * 0.4) else "#ef4444"
        else:
            elo_color = "#475569"

        chart_data = create_chart_data_for_leader(leader, all_leaders, meta_format)
        chart_data_json = json.dumps(chart_data)
        chart_data_escaped = html.escape(chart_data_json)

        price = leader_prices.get(leader.id) if leader_prices else None
        price_text = f"€{price:.2f}" if price is not None else "N/A"
        leader_url = f"/leader?lid={leader.id}&meta_format={meta_format}{f'&region={region}' if region else ''}"
        leader_name = leader.name.replace('"', " ").replace('.', " ")

        # ── Mobile card ──────────────────────────────────────────────
        mobile_card = ft.Div(
            ft.Div(
                # Header row: rank + name
                ft.Div(
                    ft.Span(f"#{idx + 1}", style="font-family:'Bebas Neue',sans-serif; font-size:1.1rem; color:#475569; margin-right:8px; letter-spacing:0.08em;"),
                    ft.A(leader_name, href=leader_url, cls="hp-leader-link truncate", style="font-size:1rem;"),
                    cls="flex items-center mb-3"
                ),
                # Image + stats
                ft.Div(
                    ft.Div(
                        cls="w-20 h-20 rounded-lg flex-shrink-0 mr-4 bg-cover bg-center",
                        style=f"background-image:url('{leader.aa_image_url}'); border:2px solid {leader.to_hex_color()};"
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span("Win Rate", cls="hp-section-label"),
                            ft.Span(f"{leader.win_rate * 100:.1f}%" if leader.win_rate is not None else "N/A",
                                    style="font-family:'Share Tech Mono',monospace; color:#f1f5f9; font-size:0.85rem;"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("Elo", cls="hp-section-label"),
                            ft.Span(str(leader.elo) if leader.elo is not None else "N/A",
                                    style=f"font-family:'Share Tech Mono',monospace; color:{elo_color}; font-size:0.85rem;"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("Matches", cls="hp-section-label"),
                            ft.Span(str(leader.total_matches) if leader.total_matches is not None else "N/A",
                                    style="font-family:'Share Tech Mono',monospace; color:#94a3b8; font-size:0.85rem;"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("Top 1", cls="hp-section-label"),
                            ft.Span(str(leader.tournament_wins),
                                    style="font-family:'Share Tech Mono',monospace; color:#f59e0b; font-size:0.85rem;"),
                            cls="text-center"
                        ),
                        ft.Div(
                            ft.Span("D-Score", cls="hp-section-label"),
                            ft.Span(f"{int(leader.d_score * 100)}%" if leader.d_score is not None else "N/A",
                                    style="font-family:'Share Tech Mono',monospace; color:#94a3b8; font-size:0.85rem;"),
                            cls="text-center"
                        ),
                        cls="grid grid-cols-3 gap-2 flex-grow"
                    ),
                    cls="flex"
                ),
                # Footer: set + price
                ft.Div(
                    ft.Span(f"Set: {leader.id.split('-')[0]}", style="font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#475569;"),
                    ft.Span(price_text, style="font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#94a3b8;"),
                    cls="flex justify-between mt-3 pt-3", style="border-top:1px solid #1a2540;"
                ),
                # Spark chart
                ft.Div(
                    create_loading_overlay(id=f"chart-loading-mobile-{leader.id}", size="w-8 h-8"),
                    ft.Div(
                        id=f"leader-chart-mobile-{leader.id}",
                        hx_post=f"/api/leader-chart/{leader.id}",
                        hx_trigger="intersect once",
                        hx_swap="innerHTML",
                        hx_target=f"#leader-chart-mobile-{leader.id}",
                        hx_include=HX_INCLUDE,
                        hx_indicator=f"#chart-loading-mobile-{leader.id}",
                        hx_vals=f'{{"chart_data": "{chart_data_escaped}"}}',
                        cls="w-full",
                        style="height:80px;",
                        data_chart_data=chart_data_json
                    ),
                    cls="relative w-full mt-3 pt-3",
                    style="height:80px; border-top:1px solid #1a2540;"
                ),
                cls="hp-panel p-4 text-left"
            )
        )
        mobile_cards.append(mobile_card)

        # ── Desktop row ──────────────────────────────────────────────
        cells = [
            ft.Td(
                ft.Div(
                    ft.Div(f"#{idx + 1}", cls="rank-text"),
                    cls="leaderboard-image-cell",
                    style=f"background-image: linear-gradient(to top, {leader.to_hex_color()}, transparent), url('{leader.aa_image_url}')"
                ),
                cls="p-0"
            ),
            ft.Td(
                ft.A(leader_name, href=leader_url, cls="hp-leader-link"),
                cls="hp-td", style="text-align:center; vertical-align:middle;"
            ),
            ft.Td(leader.id.split("-")[0], cls="hp-td-mono"),
            ft.Td(str(leader.tournament_wins), cls="hp-td-mono", style="color:#f59e0b;"),
            ft.Td(str(leader.total_matches) if leader.total_matches is not None else "N/A", cls="hp-td-mono"),
            ft.Td(f"{leader.win_rate * 100:.2f}%" if leader.win_rate is not None else "N/A", cls="hp-td-mono"),
            ft.Td(f"{int(leader.d_score * 100)}%" if leader.d_score is not None else "N/A", cls="hp-td-mono"),
            ft.Td(price_text, cls="hp-td-mono"),
            ft.Td(str(leader.elo) if leader.elo is not None else "N/A", cls="hp-td-mono",
                  style=f"color:{elo_color};"),
            ft.Td(
                ft.Div(
                    create_loading_overlay(id=f"chart-loading-{leader.id}", size="w-8 h-8"),
                    ft.Div(
                        id=f"leader-chart-{leader.id}",
                        hx_post=f"/api/leader-chart/{leader.id}",
                        hx_trigger="intersect once",
                        hx_swap="innerHTML",
                        hx_target=f"#leader-chart-{leader.id}",
                        hx_include=HX_INCLUDE,
                        hx_indicator=f"#chart-loading-{leader.id}",
                        hx_vals=f'{{"chart_data": "{chart_data_escaped}"}}',
                        cls="w-[160px]",
                        style="height:100px;",
                        data_chart_data=chart_data_json
                    ),
                    cls="relative w-[160px]",
                    style="height:100px;"
                ),
                cls="px-0 py-0 min-w-[160px] relative",
                style="height:100px;"
            ),
        ]
        rows.append(ft.Tr(*cells, cls="hp-tr"))

    body = ft.Tbody(*rows)

    table_container = ft.Div(
        create_loading_spinner(id="leaderboard-loading", size="w-12 h-12",
                               container_classes="htmx-indicator w-full h-[200px]"),
        ft.Table(
            header, body,
            cls="min-w-full divide-y hidden md:table",
            style="border-collapse:collapse; table-layout:fixed; width:100%;"
        ),
        ft.Div(*mobile_cards, cls="md:hidden space-y-4 text-left"),
        cls="relative",
        hx_indicator="#leaderboard-loading"
    )

    return table_container


def home_page():
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

    return ft.Div(
        _styles(),
        ft.H1(
            "Leaderboard",
            style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; margin-bottom:20px;"
        ),
        ft.Div(
            ft.Div(
                create_mobile_filter_button(),
                create_loading_spinner(id="loading-indicator", size="w-8 h-8",
                                       container_classes="min-h-[100px]"),
                ft.Div(
                    hx_get="/api/leaderboard",
                    hx_trigger="load",
                    hx_include=HX_INCLUDE,
                    hx_target="#leaderboard-table",
                    hx_indicator="#loading-indicator",
                    id="leaderboard-table"
                ),
                cls="relative"
            ),
            cls="space-y-4 w-full overflow-x-auto"
        ),
        persist_script,
        cls="hp-page relative"
    )
