from fasthtml import ft
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.filters import create_leader_select_component
from op_tcg.frontend.components.effect_text import render_effect_text

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='lid'],[name='region']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/leader-data",
    "hx_trigger": "change",
    "hx_target": "#leader-content-inner",
    "hx_swap": "outerHTML",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#leader-page-loading"
    # Note: URL updates are handled by JavaScript to maintain /leader path
}


def _styles() -> ft.Style:
    return ft.Style("""
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.lp-page { font-family: 'Barlow', sans-serif; }
.lp-display { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.08em; }
.lp-mono { font-family: 'Share Tech Mono', monospace; }

.lp-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
}

.lp-panel-sm {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 8px;
}

.lp-select {
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
.lp-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }

.lp-section-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.12em;
    color: #334155;
    font-size: 0.65rem;
    text-transform: uppercase;
    margin-bottom: 6px;
}

/* Tab system */
.lp-tab-bar {
    display: flex;
    border-bottom: 1px solid #1a2540;
    padding: 0 4px;
    gap: 2px;
}

.lp-tab-btn {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    font-size: 0.9rem;
    color: #475569;
    background: transparent;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 18px 8px;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    margin-bottom: -1px;
}
.lp-tab-btn:hover { color: #94a3b8; }
.lp-tab-btn.active {
    color: #38bdf8;
    border-bottom-color: #38bdf8;
}

.lp-tab-pane { display: none; }
.lp-tab-pane.active { display: block; }

/* Attribute pill */
.lp-attr-pill {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.65rem;
    color: #94a3b8;
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 4px;
    padding: 2px 7px;
}

/* Leader image glow on hover */
.lp-leader-img-wrap {
    border-radius: 10px;
    overflow: hidden;
    border: 1px solid #1a2540;
    transition: border-color 0.2s, box-shadow 0.2s;
}
.lp-leader-img-wrap:hover {
    border-color: rgba(245,158,11,0.5);
    box-shadow: 0 0 28px rgba(245,158,11,0.12);
}

/* View decklists button */
.lp-btn-cta {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    background: #f59e0b;
    color: #000;
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    font-size: 0.95rem;
    padding: 9px 24px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: background 0.12s, transform 0.1s;
}
.lp-btn-cta:hover { background: #fbbf24; transform: translateY(-1px); }
.lp-btn-cta:active { transform: scale(0.97); transition-duration: 0.06s; }

/* Scrollbar */
::-webkit-scrollbar { width: 3px; }
::-webkit-scrollbar-track { background: transparent; }
::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 2px; }

/* Desktop two-column layout */
@media (min-width: 768px) {
    .lp-layout-main { flex-direction: row !important; }
    .lp-left-col { width: 240px !important; }
    .lp-charts-col { flex: 1; min-width: 0; }
    .lp-decklist-row { flex-direction: row !important; }
}

/* Entrance animation */
@keyframes lp-fade-up {
    from { opacity: 0; transform: translateY(5px); }
    to   { opacity: 1; transform: translateY(0); }
}
.lp-enter { animation: lp-fade-up 0.3s ease both; }
.lp-enter-1 { animation-delay: 0.05s; }
.lp-enter-2 { animation-delay: 0.10s; }
.lp-enter-3 { animation-delay: 0.15s; }
.lp-enter-4 { animation-delay: 0.20s; }
""")


def create_filter_components(selected_meta_formats=None, selected_leader_id=None, selected_region=None):
    """Create filter components for the leader page."""
    latest_meta = MetaFormat.latest_meta_format()

    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]

    if not selected_region:
        selected_region = MetaFormatRegion.ALL

    # Meta format select
    meta_format_select = ft.Div(
        ft.Div("Meta Format", cls="lp-section-label"),
        ft.Select(
            id="release-meta-formats-select",
            name="meta_format",
            multiple=True,
            size=1,
            cls="lp-select multiselect",
            *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats)) for mf in reversed(MetaFormat.to_list(region=MetaFormatRegion.ASIA))],
            **{
                "hx_get": "/api/leader-select",
                "hx_target": "#leader-select-wrapper",
                "hx_include": HX_INCLUDE,
                "hx_trigger": "change",
                "hx_swap": "innerHTML",
                "hx_params": "*"
            }
        )
    )

    # Region select
    regions = MetaFormatRegion.to_list()
    region_select = ft.Div(
        ft.Div("Region", cls="lp-section-label"),
        ft.Select(
            id="region-select",
            name="region",
            cls="lp-select styled-select",
            *[ft.Option(r, value=r, selected=(r == selected_region)) for r in regions],
            **{
                "hx_get": "/api/leader-select",
                "hx_target": "#leader-select-wrapper",
                "hx_include": HX_INCLUDE,
                "hx_trigger": "change",
                "hx_swap": "innerHTML",
                "hx_params": "*"
            }
        )
    )

    content_trigger = ft.Div(
        id="content-trigger",
        **FILTER_HX_ATTRS,
        style="display: none;"
    )

    trigger_script = ft.Script("""
        function updateLeaderURL() {
            const params = new URLSearchParams();
            const metaFormatSelect = document.querySelector('[name="meta_format"]');
            if (metaFormatSelect) {
                Array.from(metaFormatSelect.selectedOptions).forEach(opt => {
                    if (opt.value) params.append('meta_format', opt.value);
                });
            }
            const leaderSelect = document.querySelector('[name="lid"]');
            if (leaderSelect && leaderSelect.value) params.set('lid', leaderSelect.value);
            const regionSelect = document.querySelector('[name="region"]');
            if (regionSelect && regionSelect.value) params.set('region', regionSelect.value);
            const newURL = '/leader' + (params.toString() ? '?' + params.toString() : '');
            window.history.replaceState({}, '', newURL);
        }

        document.addEventListener('htmx:afterSettle', function(evt) {
            if (evt.target.id === 'leader-select-wrapper') {
                setTimeout(function() {
                    const leaderSelect = document.querySelector('[name="lid"]');
                    if (leaderSelect && leaderSelect.value) {
                        updateLeaderURL();
                        htmx.trigger('#content-trigger', 'change');
                    }
                }, 50);
            }
            if (evt.target.id === 'leader-content') updateLeaderURL();
        });

        document.addEventListener('change', function(evt) {
            if (evt.target.matches('[name="meta_format"], [name="region"], [name="lid"]')) {
                setTimeout(updateLeaderURL, 10);
            }
        });

        document.addEventListener('DOMContentLoaded', function() {
            setTimeout(updateLeaderURL, 100);
        });
    """)

    initial_leader_input = ft.Input(
        type="hidden",
        name="initial_lid",
        value=selected_leader_id or "",
        id="initial-leader-id"
    ) if selected_leader_id else None

    leader_select_htmx_attrs = {
        "hx_get": "/api/leader-select",
        "hx_trigger": "load",
        "hx_include": HX_INCLUDE + ",[name='initial_lid']",
        "hx_target": "this",
        "hx_swap": "innerHTML",
        "hx_indicator": "#leader-select-loading"
    }

    leader_select_wrapper = ft.Div(
        ft.Div("Leader", cls="lp-section-label"),
        ft.Div(
            create_loading_spinner(id="leader-select-loading", size="w-6 h-6", container_classes="min-h-[60px]"),
            **leader_select_htmx_attrs,
            id="leader-select-wrapper",
            cls="relative"
        )
    )

    components = [
        meta_format_select,
        region_select,
        leader_select_wrapper,
        content_trigger,
        trigger_script,
    ]
    if initial_leader_input:
        components.append(initial_leader_input)

    return ft.Div(*components, cls="space-y-4")


def create_tab_view(has_match_data: bool = True):
    """Create a tabbed interface for the leader page content."""

    tab_buttons = [
        ft.Button(
            "Decklist Analysis",
            cls="lp-tab-btn active",
            onclick="lpSwitchTab(event, 'decklist-tab')",
            id="decklist-button"
        )
    ]

    if has_match_data:
        tab_buttons.append(
            ft.Button(
                "Matchup Analysis",
                cls="lp-tab-btn",
                onclick="lpSwitchTab(event, 'matchup-tab')",
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
            cls="lp-tab-btn",
            onclick="lpSwitchTab(event, 'tournaments-tab')",
            hx_get="/api/leader-tournaments",
            hx_trigger="click once",
            hx_target="#tournaments-tab",
            hx_indicator="#tournament-loading-indicator",
            hx_include=HX_INCLUDE,
            id="tournaments-button"
        )
    )

    tab_content = [
        ft.Div(
            ft.Div(
                ft.H2("Decklist Analysis", cls="lp-display", style="font-size:1.4rem; color:#f1f5f9; margin:0;"),
                ft.Button(
                    ft.Span("View Tournament Decklists"),
                    ft.Span("→"),
                    cls="lp-btn-cta",
                    hx_get="/api/decklist-modal",
                    hx_target="body",
                    hx_swap="beforeend",
                    hx_include=HX_INCLUDE
                ),
                style="display:flex; align-items:center; justify-content:space-between; flex-wrap:wrap; gap:12px; margin-bottom:20px;"
            ),
            ft.Div(
                # Left — Decklist
                ft.Div(
                    create_loading_spinner(id="decklist-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
                    ft.Div(
                        hx_get="/api/leader-decklist",
                        hx_trigger="load",
                        hx_include=HX_INCLUDE,
                        hx_target="#leader-decklist-container",
                        hx_indicator="#decklist-loading-indicator",
                        id="leader-decklist-container",
                        cls="min-h-[300px] w-full"
                    ),
                    cls="lp-panel", style="padding:16px; flex:1; min-width:0;"
                ),
                # Right — Similar Leader
                ft.Div(
                    create_loading_spinner(id="similar-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
                    ft.Div(
                        hx_get="/api/leader-similar",
                        hx_trigger="load",
                        hx_include=HX_INCLUDE,
                        hx_target="#leader-similar-container",
                        hx_indicator="#similar-loading-indicator",
                        id="leader-similar-container",
                        cls="min-h-[300px] w-full"
                    ),
                    cls="lp-panel", style="padding:16px; flex:1; min-width:0;"
                ),
                cls="lp-decklist-row", style="display:flex; flex-direction:column; gap:16px;"
            ),
            cls="lp-tab-pane active",
            id="decklist-tab",
            style="padding:20px 16px;"
        )
    ]

    if has_match_data:
        tab_content.append(
            ft.Div(
                create_loading_spinner(id="matchup-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
                cls="lp-tab-pane",
                id="matchup-tab",
            )
        )

    tab_content.append(
        ft.Div(
            create_loading_spinner(id="tournament-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
            cls="lp-tab-pane",
            id="tournaments-tab",
            style="padding:20px 16px;"
        )
    )

    return ft.Div(
        ft.Div(*tab_buttons, cls="lp-tab-bar"),
        ft.Div(*tab_content),
        ft.Script("""
            function lpSwitchTab(event, tabId) {
                document.querySelectorAll('.lp-tab-btn').forEach(b => b.classList.remove('active'));
                event.currentTarget.classList.add('active');
                document.querySelectorAll('.lp-tab-pane').forEach(p => p.classList.remove('active'));
                document.getElementById(tabId).classList.add('active');
            }
        """),
        cls="lp-panel", style="overflow:hidden;"
    )


def create_leader_content(leader_id: str, leader_name: str, aa_image_url: str, total_matches: int | None = None, ability: str | None = None, attributes: list[str] | None = None):
    """Create the content for a leader page."""
    has_match_data = total_matches is not None and total_matches > 0

    charts_section = ft.Div(
        # Win rate chart
        ft.Div(
            ft.Div("Win Rate History", cls="lp-display lp-enter lp-enter-1", style="font-size:1.1rem; color:#f1f5f9; margin-bottom:12px;"),
            create_loading_spinner(id="win-rate-chart-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
            ft.Div(
                hx_get=f"/api/leader-chart/{leader_id}",
                hx_trigger="load",
                hx_include=HX_INCLUDE,
                hx_target="#win-rate-chart-container",
                hx_indicator="#win-rate-chart-loading-indicator",
                hx_vals=f'{{"last_n": "10", "color": "neutral"}}',
                id="win-rate-chart-container",
                cls="w-full",
                style="height: 150px;"
            ),
            cls="lp-panel lp-enter lp-enter-2", style="padding:20px; margin-bottom:16px;"
        ),
        # Radar chart
        ft.Div(
            ft.Div("Color Matchups", cls="lp-display lp-enter lp-enter-3", style="font-size:1.1rem; color:#f1f5f9; margin-bottom:12px;"),
            create_loading_spinner(id="radar-chart-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
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
            cls="lp-panel lp-enter lp-enter-4", style="padding:20px;"
        ),
        cls="lp-charts-col", style="min-width:0; display:flex; flex-direction:column;"
    )

    # Attribute pills
    attr_pills = ft.Div(
        *([ft.Span(str(a), cls="lp-attr-pill") for a in (attributes or [])] or []),
        style="display:flex; flex-wrap:wrap; gap:4px; margin-bottom:10px;"
    )

    # Effect / ability block
    ability_block = ft.Div(
        ft.Div("Effect", cls="lp-section-label"),
        ft.Div(
            render_effect_text(ability or "", subject_name=leader_name),
            style="max-height:96px; overflow-y:auto; color:#94a3b8; font-size:0.8rem; line-height:1.5;"
        ),
        cls="lp-panel-sm", style="padding:12px; margin-bottom:12px;"
    )

    # Stats block
    stats_block = ft.Div(
        ft.Div("Stats", cls="lp-section-label"),
        create_loading_spinner(id="stats-loading-indicator", size="w-8 h-8", container_classes="min-h-[100px]"),
        ft.Div(
            hx_get="/api/leader-stats",
            hx_trigger="load",
            hx_include=HX_INCLUDE,
            hx_target="#leader-stats-container",
            hx_indicator="#stats-loading-indicator",
            id="leader-stats-container",
            cls="space-y-2"
        ),
        cls="lp-panel-sm", style="padding:12px;"
    )

    left_col = ft.Div(
        ft.Div(
            ft.Img(src=aa_image_url, cls="w-full", style="display:block;"),
            cls="lp-leader-img-wrap lp-enter", style="margin-bottom:14px;"
        ),
        attr_pills,
        ability_block,
        stats_block,
        cls="lp-left-col", style="flex-shrink:0;"
    )

    return ft.Div(
        _styles(),
        ft.H1(
            ft.Span(leader_name, cls="lp-display", style="font-size:2rem; color:#f1f5f9; letter-spacing:0.08em;"),
            ft.Span(f" {leader_id}", cls="lp-mono", style="font-size:0.85rem; color:#475569; margin-left:8px;"),
            style="margin-bottom:24px; display:flex; align-items:baseline; flex-wrap:wrap; gap:4px;"
        ),
        # Two-column layout: left sidebar + charts
        ft.Div(
            left_col,
            charts_section,
            cls="lp-layout-main", style="display:flex; flex-direction:column; gap:16px; margin-bottom:20px;"
        ),
        # Tab view
        ft.Div(create_tab_view(has_match_data)),
        id="leader-content-inner",
        data_leader_id=leader_id,
        cls="lp-page"
    )


def leader_page(leader_id: str | None = None, filtered_leader_data: LeaderExtended | None = None, selected_meta_format: list | None = None):
    """Display detailed information about a specific leader."""

    if filtered_leader_data:
        leader_data = filtered_leader_data
    else:
        htmx_attrs = {
            "hx_get": "/api/leader-data",
            "hx_include": HX_INCLUDE,
            "hx_target": "#leader-content-inner",
            "hx_swap": "outerHTML"
        }
        if leader_id:
            htmx_attrs["hx_vals"] = f'{{"lid": "{leader_id}"}}'

        return ft.Div(
            _styles(),
            create_loading_spinner(
                id="leader-page-loading",
                size="w-8 h-8",
                container_classes="absolute inset-0 z-50 backdrop-blur-sm",
            ),
            ft.Div(
                **htmx_attrs,
                id="leader-content-inner",
                cls="mt-8"
            ),
            cls="lp-page min-h-screen p-0 lg:p-8 relative",
            id="leader-content"
        )

    if not leader_data:
        return ft.Div(
            _styles(),
            ft.P("No data available for this leader.", style="color:#ef4444; font-family:'Barlow',sans-serif;"),
            cls="lp-page min-h-screen p-8",
            id="leader-content"
        )

    leader_content = create_leader_content(
        leader_id=leader_data.id,
        leader_name=leader_data.name,
        aa_image_url=leader_data.aa_image_url,
        total_matches=leader_data.total_matches,
        ability=leader_data.ability if hasattr(leader_data, "ability") else None,
        attributes=[str(a) for a in getattr(leader_data, "attributes", [])] if hasattr(leader_data, "attributes") else None
    )

    return ft.Div(
        _styles(),
        create_loading_spinner(
            id="leader-page-loading",
            size="w-8 h-8",
            container_classes="absolute inset-0 z-50 backdrop-blur-sm",
        ),
        leader_content,
        cls="lp-page min-h-screen p-0 lg:p-8 relative",
        id="leader-content"
    )
