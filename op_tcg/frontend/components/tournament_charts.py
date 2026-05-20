"""Reusable tournament chart components (decklist donut + leader popularity bubble)."""

from fasthtml import ft

from op_tcg.frontend.components.loading import create_loading_overlay

_SELECT_CLS = "meta-select styled-select"
_HX_INCLUDE_BASE = "[name='meta_format'],[name='region']"


def create_decklist_popularity_section(id_prefix: str = "", extra_triggers: str = "") -> ft.Div:
    """Decklist popularity donut chart card with Timeframe/Placing filters and Leaders/Colors toggle.

    Args:
        id_prefix: Prefix for all element IDs to allow multiple instances on different pages.
        extra_triggers: Additional HTMX trigger clauses appended to the chart container's
            hx-trigger (e.g. "metaRangeChanged from:body, change from:#region-select").
    """
    p = id_prefix  # shorthand
    donut_id = f"{p}decklist-donut"
    loading_id = f"{p}decklist-donut-loading"
    view_mode_id = f"{p}donut-view-mode"
    leaders_btn_id = f"{p}donut-toggle-leaders"
    colors_btn_id = f"{p}donut-toggle-colors"
    hx_include = _HX_INCLUDE_BASE + ",[name='days'],[name='placing'],[name='view_mode']"
    trigger = "load" + (f", {extra_triggers}" if extra_triggers else "")

    return ft.Div(
        ft.Span("Tournament Decklist Popularity", cls="meta-panel-title", style="font-size:1.05rem; margin-bottom:12px; display:block;"),
        ft.Input(type="hidden", name="view_mode", value="leaders", id=view_mode_id),
        ft.Div(
            ft.Div(
                ft.Span("Timeframe", cls="meta-section-label"),
                ft.Select(
                    ft.Option("Last 7 days", value="7"),
                    ft.Option("Last 14 days", value="14", selected=True),
                    ft.Option("Last 30 days", value="30"),
                    ft.Option("Last 90 days", value="90"),
                    ft.Option("All", value="all"),
                    name="days",
                    cls=_SELECT_CLS,
                    hx_get="/api/tournaments/decklist-donut-smart",
                    hx_trigger="change",
                    hx_target=f"#{donut_id}",
                    hx_include=hx_include,
                    hx_indicator=f"#{loading_id}",
                ),
                cls="flex-1",
            ),
            ft.Div(
                ft.Span("Tournament Placing", cls="meta-section-label"),
                ft.Select(
                    ft.Option("All", value="all", selected=True),
                    ft.Option("Top 1", value="1"),
                    ft.Option("Top 4", value="4"),
                    ft.Option("Top 8", value="8"),
                    name="placing",
                    cls=_SELECT_CLS,
                    hx_get="/api/tournaments/decklist-donut-smart",
                    hx_trigger="change",
                    hx_target=f"#{donut_id}",
                    hx_include=hx_include,
                    hx_indicator=f"#{loading_id}",
                ),
                cls="flex-1",
            ),
            cls="flex flex-col md:flex-row gap-3 mb-4",
        ),
        ft.Div(
            ft.Div(
                ft.Button(
                    "Leaders",
                    id=leaders_btn_id,
                    cls="meta-toggle-btn active",
                    aria_pressed="true",
                    hx_get="/api/tournaments/decklist-donut-smart",
                    hx_trigger="click",
                    hx_target=f"#{donut_id}",
                    hx_include=hx_include,
                    hx_indicator=f"#{loading_id}",
                ),
                ft.Button(
                    "Colors",
                    id=colors_btn_id,
                    cls="meta-toggle-btn",
                    aria_pressed="false",
                    hx_get="/api/tournaments/decklist-donut-smart",
                    hx_trigger="click",
                    hx_target=f"#{donut_id}",
                    hx_include=hx_include,
                    hx_indicator=f"#{loading_id}",
                ),
                cls="meta-toggle-group mb-3",
                role="group",
                aria_label="Donut view mode",
            ),
            ft.Div(
                create_loading_overlay(id=loading_id, size="w-8 h-8"),
                ft.Div(
                    id=donut_id,
                    hx_get="/api/tournaments/decklist-donut-smart",
                    hx_trigger=trigger,
                    hx_include=hx_include,
                    hx_indicator=f"#{loading_id}",
                    cls="w-full h-full",
                ),
                cls="meta-chart-area relative",
                style="min-height: 200px; width: 100%;",
            ),
            ft.Script(f"""
                (function(){{
                  var leadersBtn  = document.getElementById('{leaders_btn_id}');
                  var colorsBtn   = document.getElementById('{colors_btn_id}');
                  var viewModeInput = document.getElementById('{view_mode_id}');
                  if (!leadersBtn || !colorsBtn || !viewModeInput) return;
                  function activate(isLeaders){{
                    viewModeInput.value = isLeaders ? 'leaders' : 'colors';
                    leadersBtn.classList.toggle('active', isLeaders);
                    colorsBtn.classList.toggle('active', !isLeaders);
                    leadersBtn.setAttribute('aria-pressed', isLeaders ? 'true' : 'false');
                    colorsBtn.setAttribute('aria-pressed', isLeaders ? 'false' : 'true');
                  }}
                  activate(true);
                  leadersBtn.addEventListener('click', function(){{ activate(true); }});
                  colorsBtn.addEventListener('click',  function(){{ activate(false); }});
                }})();
            """),
        ),
        cls="meta-panel",
    )


def create_leader_popularity_section(id_prefix: str = "", extra_triggers: str = "", data_tooltip: str | None = None) -> ft.Div:
    """Tournament leader popularity bubble chart card with match count range slider.

    Args:
        id_prefix: Prefix for all element IDs to allow multiple instances on different pages.
        extra_triggers: Additional HTMX trigger clauses appended to the chart container's
            hx-trigger (e.g. "metaRangeChanged from:body, change from:#region-select").
    """
    data_tooltip = data_tooltip or "Size of the bubbles increases with the tournament wins"
    p = id_prefix
    chart_container_id = f"{p}tournament-chart-container"
    loading_id = f"{p}tournament-chart-loading"
    slider_id = f"{p}match-slider"
    slider_id_input_id = f"{p}slider-id-input"
    hx_include = _HX_INCLUDE_BASE + f",[name='min_matches'],[name='max_matches'],[id='{slider_id_input_id}']"
    trigger = "load" + (f", {extra_triggers}" if extra_triggers else "")

    return ft.Div(
        ft.Span(
            "Tournament Leader Popularity ",
            ft.Span(
                "ⓘ",
                id=f"{p}bubble-chart-tooltip",
                cls="cursor-help",
                style="font-family:'Barlow',sans-serif; font-size:0.7rem; color:#334155;",
                data_tooltip=data_tooltip,
            ),
            cls="meta-panel-title",
            style="font-size:1.05rem; margin-bottom:12px; display:block;",
        ),
        # Hidden input so every request carries the page-specific slider ID
        ft.Input(type="hidden", name="slider_id", value=slider_id, id=slider_id_input_id),
        ft.Div(
            create_loading_overlay(id=loading_id, size="w-8 h-8"),
            ft.Div(
                id=chart_container_id,
                hx_get="/api/tournaments/chart",
                hx_trigger=trigger,
                hx_indicator=f"#{loading_id}",
                hx_include=hx_include,
                cls="w-full h-full",
            ),
            cls="meta-chart-area relative",
            style="height: auto; width: 100%;",
        ),
        ft.Div(
            ft.Span("Tournament Match Count Range", cls="meta-section-label"),
            ft.Div(
                ft.Div(
                    ft.Div(cls="slider-track"),
                    ft.Input(
                        type="range", min="0", max="1000", value="0",
                        name="min_matches", cls="slider-range min-range",
                        hx_get="/api/tournaments/chart",
                        hx_trigger="change",
                        hx_sync="closest .double-range-slider:queue last",
                        hx_target=f"#{chart_container_id}",
                        hx_include=hx_include,
                        hx_indicator=f"#{loading_id}",
                    ),
                    ft.Input(
                        type="range", min="0", max="1000", value="1000",
                        name="max_matches", cls="slider-range max-range",
                        hx_get="/api/tournaments/chart",
                        hx_trigger="change",
                        hx_sync="closest .double-range-slider:queue last",
                        hx_target=f"#{chart_container_id}",
                        hx_include=hx_include,
                        hx_indicator=f"#{loading_id}",
                    ),
                    ft.Div(
                        ft.Span("0", cls="min-value"),
                        ft.Span(" – ", style="color:#334155; margin:0 4px;"),
                        ft.Span("1000", cls="max-value"),
                        cls="slider-values",
                    ),
                    cls="double-range-slider",
                    id=slider_id,
                    data_double_range_slider="true",
                ),
                cls="relative w-full",
            ),
            cls="mt-4",
        ),
        ft.Script(f"""
            document.addEventListener('htmx:beforeRequest', function(event) {{
                if (event.target && event.target.id === '{chart_container_id}') {{
                    var canvas = document.getElementById('tournament-chart');
                    if (canvas) {{
                        canvas.style.visibility = 'hidden';
                        canvas.style.pointerEvents = 'none';
                    }}
                }}
            }});
            document.addEventListener('htmx:afterSwap', function(event) {{
                if (event.target && event.target.id === '{chart_container_id}') {{
                    setTimeout(function() {{
                        if (window.recreateBubbleChart) window.recreateBubbleChart();
                        var canvas = document.getElementById('tournament-chart');
                        if (canvas) {{
                            requestAnimationFrame(function() {{
                                canvas.style.visibility = 'visible';
                                canvas.style.pointerEvents = '';
                            }});
                        }}
                    }}, 100);
                }}
            }});
        """),
        cls="meta-panel",
    )
