import json

from fasthtml import ft

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.tournament_charts import (
    create_decklist_popularity_section,
    create_leader_popularity_section,
)

HX_INCLUDE = "[name='region'],[name='from_meta_idx'],[name='to_meta_idx'],[name='meta_view_mode']"

FILTER_HX_ATTRS = {
    "hx_get": "/api/meta-share-chart",
    "hx_trigger": "change",
    "hx_target": "#meta-share-chart",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#meta-loading-indicator",
}

HX_INCLUDE_DETAIL = "[name='region'],[name='meta_format'],[name='detail_view_mode']"

FILTER_HX_ATTRS_DETAIL = {
    "hx_get": "/api/meta-detail-chart",
    "hx_trigger": "change",
    "hx_target": "#meta-detail-chart",
    "hx_swap": "innerHTML",
    "hx_include": HX_INCLUDE_DETAIL,
    "hx_indicator": "#meta-detail-loading-indicator",
}


def _styles() -> ft.Style:
    return ft.Style("""
.meta-page { font-family: 'Barlow', sans-serif; }

.meta-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
    padding: 20px;
}
@media (min-width: 768px) { .meta-panel { padding: 24px 28px; } }

.meta-select {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 8px 12px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.875rem;
    outline: none;
    cursor: pointer;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.meta-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }

.meta-section-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    color: #334155;
    font-size: 0.65rem;
    text-transform: uppercase;
    display: block;
    margin-bottom: 6px;
}

.meta-panel-title {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.12em;
    font-size: 1.15rem;
    color: #f1f5f9;
    line-height: 1;
    display: block;
}

.meta-panel-sub {
    font-family: 'Barlow', sans-serif;
    font-size: 0.7rem;
    color: #334155;
    margin-top: 4px;
    display: block;
}

.meta-toggle-group {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    padding: 3px;
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 24px;
    flex-shrink: 0;
}

.meta-toggle-btn {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    padding: 4px 16px;
    border-radius: 20px;
    border: 1px solid transparent;
    background: transparent;
    color: #475569;
    cursor: pointer;
    transition: all 0.12s;
    white-space: nowrap;
}
.meta-toggle-btn:hover { color: #64748b; }
.meta-toggle-btn.active {
    background: rgba(56,189,248,0.1);
    color: #38bdf8;
    border-color: rgba(56,189,248,0.3);
}

.meta-chart-area {
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 8px;
    overflow: hidden;
    padding: 8px;
}

.meta-range-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    color: #334155;
    font-size: 0.65rem;
    text-transform: uppercase;
    display: block;
    margin-bottom: 8px;
}

.slider-values {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #38bdf8;
}
""")


def _panel_header(title: str, subtitle: str, toggle_leaders_id: str, toggle_colors_id: str,
                  hx_get: str, hx_target: str, hx_include: str, hx_indicator: str,
                  view_mode_input_id: str, tooltip: str | None = None) -> ft.Div:
    title_el = ft.Div(
        ft.Span(
            title,
            ft.Span(
                "ⓘ",
                cls="cursor-help",
                style="font-family:'Barlow',sans-serif;font-size:0.7rem;color:#334155;margin-left:6px;",
                data_tooltip=tooltip,
            ) if tooltip else "",
            cls="meta-panel-title",
        ),
        ft.Span(subtitle, cls="meta-panel-sub"),
    )
    toggle = ft.Div(
        ft.Input(type="hidden", name=("detail_view_mode" if "detail" in view_mode_input_id else "meta_view_mode"),
                 value="leaders", id=view_mode_input_id),
        ft.Div(
            ft.Button(
                "Leaders",
                id=toggle_leaders_id,
                cls="meta-toggle-btn active",
                aria_pressed="true",
                hx_get=hx_get,
                hx_trigger="click",
                hx_target=hx_target,
                hx_swap="innerHTML",
                hx_include=hx_include,
                hx_indicator=hx_indicator,
            ),
            ft.Button(
                "Colors",
                id=toggle_colors_id,
                cls="meta-toggle-btn",
                aria_pressed="false",
                hx_get=hx_get,
                hx_trigger="click",
                hx_target=hx_target,
                hx_swap="innerHTML",
                hx_include=hx_include,
                hx_indicator=hx_indicator,
            ),
            cls="meta-toggle-group",
            role="group",
        ),
        cls="flex flex-col items-end gap-2",
    )
    return ft.Div(title_el, toggle, cls="flex items-start justify-between mb-5 gap-4")


def _toggle_script(leaders_id: str, colors_id: str, view_input_id: str) -> ft.Script:
    return ft.Script(f"""
        (function(){{
          var leadersBtn = document.getElementById('{leaders_id}');
          var colorsBtn  = document.getElementById('{colors_id}');
          var viewInput  = document.getElementById('{view_input_id}');
          if (!leadersBtn || !colorsBtn || !viewInput) return;
          function activate(isLeaders){{
            viewInput.value = isLeaders ? 'leaders' : 'colors';
            leadersBtn.classList.toggle('active', isLeaders);
            colorsBtn.classList.toggle('active', !isLeaders);
            leadersBtn.setAttribute('aria-pressed', isLeaders ? 'true' : 'false');
            colorsBtn.setAttribute('aria-pressed', isLeaders ? 'false' : 'true');
          }}
          activate(true);
          leadersBtn.addEventListener('click', function(){{ activate(true); }});
          colorsBtn.addEventListener('click',  function(){{ activate(false); }});
        }})();
    """)


def create_filter_components(selected_region: MetaFormatRegion | None = None):
    selected_region = selected_region or MetaFormatRegion.ALL
    meta_formats = MetaFormat.to_list()

    region_select = ft.Div(
        ft.Span("Region", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(r, value=r, selected=r == selected_region) for r in MetaFormatRegion.to_list()],
            id="region-select",
            name="region",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS,
        ),
    )

    meta_format_select = ft.Div(
        ft.Span("Meta Format", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(mf, value=mf, selected=(mf == meta_formats[-1])) for mf in reversed(meta_formats)],
            name="meta_format",
            id="meta-format-select",
            cls="meta-select styled-select",
        ),
    )

    return ft.Div(region_select, meta_format_select, cls="space-y-4")


def meta_page(selected_meta_format: str | None = None):
    meta_formats = MetaFormat.to_list()
    n = len(meta_formats)
    default_from = max(0, n - 4)
    default_to = n - 1
    data_tooltip_bubble_chart = f"Meta Format: {meta_formats[-1]}. Size of the bubbles increases with the tournament wins"

    # ── Meta Detail card ──────────────────────────────────────────────────────
    meta_detail_card = ft.Div(
        _panel_header(
            title="META DETAIL",
            subtitle="Weekly tournament win share within a single meta format",
            toggle_leaders_id="detail-toggle-leaders",
            toggle_colors_id="detail-toggle-colors",
            hx_get="/api/meta-detail-chart",
            hx_target="#meta-detail-chart",
            hx_include=HX_INCLUDE_DETAIL,
            hx_indicator="#meta-detail-loading-indicator",
            view_mode_input_id="detail-view-mode-input",
            tooltip="Weekly tournament win share. Only leaders with more than 2% overall wins in the selected meta are shown.",
        ),
        create_loading_spinner(id="meta-detail-loading-indicator", size="w-8 h-8",
                               container_classes="min-h-[100px]"),
        ft.Div(
            hx_get="/api/meta-detail-chart",
            hx_trigger="load, change from:#region-select, change from:#meta-format-select",
            hx_target="this",
            hx_swap="innerHTML",
            hx_include=HX_INCLUDE_DETAIL,
            hx_indicator="#meta-detail-loading-indicator",
            id="meta-detail-chart",
            cls="w-full",
        ),
        _toggle_script("detail-toggle-leaders", "detail-toggle-colors", "detail-view-mode-input"),
        cls="meta-panel mb-4",
    )

    # ── Meta Index card ───────────────────────────────────────────────────────
    meta_index_card = ft.Div(
        _panel_header(
            title="META INDEX",
            subtitle="Tournament win share by leader or color",
            toggle_leaders_id="meta-toggle-leaders",
            toggle_colors_id="meta-toggle-colors",
            hx_get="/api/meta-share-chart",
            hx_target="#meta-share-chart",
            hx_include=HX_INCLUDE,
            hx_indicator="#meta-loading-indicator",
            view_mode_input_id="meta-view-mode-input",
            tooltip="Only leaders with more than 5% tournament win share are shown.",
        ),
        # Range slider
        ft.Div(
            ft.Span("Meta Format Range", cls="meta-range-label"),
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(
                    type="range", min="0", max=str(n - 1), value=str(default_from),
                    name="from_meta_idx", cls="slider-range min-range",
                    **FILTER_HX_ATTRS,
                ),
                ft.Input(
                    type="range", min="0", max=str(n - 1), value=str(default_to),
                    name="to_meta_idx", cls="slider-range max-range",
                    **FILTER_HX_ATTRS,
                ),
                ft.Div(
                    ft.Span(meta_formats[default_from], cls="min-value"),
                    ft.Span(" – ", style="color:#334155; margin:0 4px;"),
                    ft.Span(meta_formats[default_to], cls="max-value"),
                    cls="slider-values",
                ),
                cls="double-range-slider",
                id="meta-format-slider",
                data_double_range_slider="true",
                data_type="labels",
                data_labels=json.dumps(meta_formats),
            ),
            cls="mb-5",
        ),
        create_loading_spinner(id="meta-loading-indicator", size="w-8 h-8",
                               container_classes="min-h-[100px]"),
        ft.Div(
            hx_get="/api/meta-share-chart",
            hx_trigger="load",
            hx_target="this",
            hx_swap="innerHTML",
            hx_include=HX_INCLUDE,
            hx_indicator="#meta-loading-indicator",
            id="meta-share-chart",
            cls="w-full",
        ),
        _toggle_script("meta-toggle-leaders", "meta-toggle-colors", "meta-view-mode-input"),
        cls="meta-panel mb-4",
    )

    # ── Popularity section ────────────────────────────────────────────────────
    popularity_section = ft.Div(
        ft.Div(
            ft.Span("Decklist & Leader Popularity", cls="meta-panel-title",
                    style="font-size:1.3rem;"),
            ft.Span("Popularity charts for the selected meta format.", cls="meta-panel-sub"),
            cls="mb-5",
        ),
        ft.Div(
            ft.Div(
                create_decklist_popularity_section(
                    id_prefix="meta-",
                    extra_triggers="change from:#meta-format-select, change from:#region-select",
                ),
                cls="w-full",
            ),
            ft.Div(
                create_leader_popularity_section(
                    id_prefix="meta-",
                    extra_triggers="change from:#meta-format-select, change from:#region-select",
                    data_tooltip=data_tooltip_bubble_chart,
                ),
                cls="w-full",
            ),
            cls="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6",
        ),
    )

    return ft.Div(
        _styles(),
        ft.Div(
            # Page header
            ft.Div(
                ft.H1("META ANALYSIS",
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; line-height:1; margin-bottom:6px;"),
                ft.P(
                    "Track how tournament win share evolves across meta formats. "
                    "Use the range slider to zoom in on a period and switch between "
                    "Leaders and Colors to explore the data from different angles.",
                    style="font-family:'Barlow',sans-serif; font-size:0.875rem; color:#334155; max-width:600px;",
                ),
                cls="mb-6",
                style="padding-bottom:16px; border-bottom:1px solid #111d30;",
            ),
            meta_detail_card,
            meta_index_card,
            popularity_section,
            cls="meta-page bg-deep-navy px-4 py-4 md:px-6 md:py-6 min-h-screen",
            style="max-width:1280px; margin:0 auto;",
        ),
    )
