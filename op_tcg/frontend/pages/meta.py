import json

from fasthtml import ft

from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.tournament_charts import (
    create_decklist_popularity_section,
    create_leader_popularity_section,
)

SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

HX_INCLUDE = "[name='region'],[name='from_meta_idx'],[name='to_meta_idx'],[name='meta_view_mode']"

FILTER_HX_ATTRS = {
    "hx_get": "/api/meta-share-chart",
    "hx_trigger": "change",
    "hx_target": "#meta-share-chart",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#meta-loading-indicator",
}

HX_INCLUDE_DETAIL = "[name='region'],[name='detail_meta_format'],[name='detail_view_mode']"

FILTER_HX_ATTRS_DETAIL = {
    "hx_get": "/api/meta-detail-chart",
    "hx_trigger": "change",
    "hx_target": "#meta-detail-chart",
    "hx_swap": "innerHTML",
    "hx_include": HX_INCLUDE_DETAIL,
    "hx_indicator": "#meta-detail-loading-indicator",
}


def create_filter_components(selected_region: MetaFormatRegion | None = None):
    selected_region = selected_region or MetaFormatRegion.ALL
    meta_formats = MetaFormat.to_list()
    n = len(meta_formats)
    default_from = max(0, n - 4)
    default_to = n - 1

    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=r == selected_region) for r in MetaFormatRegion.to_list()],
        **FILTER_HX_ATTRS,
    )

    meta_slider = ft.Div(
        ft.Label("Meta Format Range", cls="text-white font-medium block mb-2"),
        ft.Div(
            ft.Div(cls="slider-track"),
            ft.Input(
                type="range",
                min="0",
                max=str(n - 1),
                value=str(default_from),
                name="from_meta_idx",
                cls="slider-range min-range",
                **FILTER_HX_ATTRS,
            ),
            ft.Input(
                type="range",
                min="0",
                max=str(n - 1),
                value=str(default_to),
                name="to_meta_idx",
                cls="slider-range max-range",
                **FILTER_HX_ATTRS,
            ),
            ft.Div(
                ft.Span(meta_formats[default_from], cls="min-value text-white"),
                ft.Span(" - ", cls="text-white mx-2"),
                ft.Span(meta_formats[default_to], cls="max-value text-white"),
                cls="slider-values",
            ),
            cls="double-range-slider",
            id="meta-format-slider",
            data_double_range_slider="true",
            data_type="labels",
            data_labels=json.dumps(meta_formats),
        ),
        cls="mb-6",
    )

    return ft.Div(region_select, meta_slider, cls="space-y-4")


def meta_page(selected_meta_format: str | None = None):
    meta_formats = MetaFormat.to_list()
    n = len(meta_formats)
    default_from = max(0, n - 4)
    default_to = n - 1

    # Default tournament charts to the latest (last) meta format so the URL
    # param reflects the most recent meta, not the first in the slider range.
    initial_meta_format = selected_meta_format or meta_formats[-1]
    default_meta_format_inputs = [
        ft.Input(type="hidden", name="meta_format", value=initial_meta_format, data_auto="1")
    ]
    data_tooltip_bubble_chart = f"Meta Format: {initial_meta_format}. Size of the bubbles increases with the tournament wins"

    return ft.Div(
        # Page header
        ft.Div(
            ft.H1("Meta Analysis", cls="text-3xl font-bold text-white"),
            ft.P(
                "Track how tournament win share evolves across meta formats. "
                "Use the range slider to zoom in on a period and switch between "
                "Leaders and Colors to explore the data from different angles.",
                cls="text-gray-400 mt-2 max-w-2xl",
            ),
            cls="mb-6",
        ),

        # Meta Detail card — date-based view within a single meta
        ft.Div(
            ft.Div(
                ft.Div(
                    ft.H2(
                        "Meta Detail",
                        ft.Span("ⓘ", cls="ml-2 cursor-help text-gray-400 text-sm font-normal",
                                data_tooltip="Weekly tournament win share. Only leaders with more than 2% overall wins in the selected meta are shown."),
                        cls="text-lg font-semibold text-white",
                    ),
                    ft.P("Weekly tournament win share within a single meta format", cls="text-xs text-gray-400 mt-0.5"),
                    cls="flex flex-col",
                ),
                ft.Input(type="hidden", name="detail_view_mode", value="leaders", id="detail-view-mode-input"),
                ft.Div(
                    ft.Button(
                        ft.Span("Leaders", cls="px-3"),
                        id="detail-toggle-leaders",
                        cls=(
                            "inline-flex items-center justify-center text-sm font-medium transition-colors "
                            "px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 "
                            "bg-blue-600 text-white shadow-sm"
                        ),
                        aria_pressed="true",
                        hx_get="/api/meta-detail-chart",
                        hx_trigger="click",
                        hx_target="#meta-detail-chart",
                        hx_swap="innerHTML",
                        hx_include=HX_INCLUDE_DETAIL,
                        hx_indicator="#meta-detail-loading-indicator",
                    ),
                    ft.Button(
                        ft.Span("Colors", cls="px-3"),
                        id="detail-toggle-colors",
                        cls=(
                            "inline-flex items-center justify-center text-sm font-medium transition-colors "
                            "px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 "
                            "bg-gray-700 text-gray-200 hover:bg-gray-600"
                        ),
                        aria_pressed="false",
                        hx_get="/api/meta-detail-chart",
                        hx_trigger="click",
                        hx_target="#meta-detail-chart",
                        hx_swap="innerHTML",
                        hx_include=HX_INCLUDE_DETAIL,
                        hx_indicator="#meta-detail-loading-indicator",
                        style="margin-left:6px;",
                    ),
                    cls=(
                        "inline-flex items-center p-1 rounded-full bg-gray-700/60 ring-1 ring-white/10 "
                        "backdrop-blur supports-[backdrop-filter]:bg-gray-700/40"
                    ),
                    role="group",
                    aria_label="Meta detail chart view mode",
                ),
                cls="flex items-start justify-between mb-4",
            ),
            ft.Select(
                *[ft.Option(mf, value=mf, selected=(mf == meta_formats[-1])) for mf in reversed(meta_formats)],
                name="detail_meta_format",
                id="detail-meta-format-select",
                cls=SELECT_CLS + " styled-select mb-4",
                **FILTER_HX_ATTRS_DETAIL,
            ),
            create_loading_spinner(
                id="meta-detail-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]",
            ),
            ft.Div(
                hx_get="/api/meta-detail-chart",
                hx_trigger="load, change from:#region-select",
                hx_target="this",
                hx_swap="innerHTML",
                hx_include=HX_INCLUDE_DETAIL,
                hx_indicator="#meta-detail-loading-indicator",
                id="meta-detail-chart",
                cls="w-full",
            ),
            cls="bg-gray-800 rounded-lg p-3 md:p-6 shadow-xl mt-8 md:mt-10",
        ),
        ft.Br(),

        # Meta Index card
        ft.Div(
            # Card header row: title left, toggle right
            ft.Div(
                ft.Div(
                    ft.H2(
                        "Meta Index",
                        ft.Span("ⓘ", cls="ml-2 cursor-help text-gray-400 text-sm font-normal", data_tooltip="Only leaders with more than 5% tournament win share are shown."),
                        cls="text-lg font-semibold text-white",
                    ),
                    ft.P("Tournament win share by leader or color", cls="text-xs text-gray-400 mt-0.5"),
                    cls="flex flex-col",
                ),
                # View-mode toggle (persists across HTMX chart reloads)
                ft.Input(type="hidden", name="meta_view_mode", value="leaders", id="meta-view-mode-input"),
                ft.Div(
                    ft.Button(
                        ft.Span("Leaders", cls="px-3"),
                        id="meta-toggle-leaders",
                        cls=(
                            "inline-flex items-center justify-center text-sm font-medium transition-colors "
                            "px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 "
                            "bg-blue-600 text-white shadow-sm"
                        ),
                        aria_pressed="true",
                        hx_get="/api/meta-share-chart",
                        hx_trigger="click",
                        hx_target="#meta-share-chart",
                        hx_swap="innerHTML",
                        hx_include=HX_INCLUDE,
                        hx_indicator="#meta-loading-indicator",
                    ),
                    ft.Button(
                        ft.Span("Colors", cls="px-3"),
                        id="meta-toggle-colors",
                        cls=(
                            "inline-flex items-center justify-center text-sm font-medium transition-colors "
                            "px-3 py-1 rounded-full focus:outline-none focus:ring-2 focus:ring-blue-400 "
                            "bg-gray-700 text-gray-200 hover:bg-gray-600"
                        ),
                        aria_pressed="false",
                        hx_get="/api/meta-share-chart",
                        hx_trigger="click",
                        hx_target="#meta-share-chart",
                        hx_swap="innerHTML",
                        hx_include=HX_INCLUDE,
                        hx_indicator="#meta-loading-indicator",
                        style="margin-left:6px;",
                    ),
                    cls=(
                        "inline-flex items-center p-1 rounded-full bg-gray-700/60 ring-1 ring-white/10 "
                        "backdrop-blur supports-[backdrop-filter]:bg-gray-700/40"
                    ),
                    role="group",
                    aria_label="Meta chart view mode",
                ),
                cls="flex items-start justify-between mb-4",
            ),
            create_loading_spinner(
                id="meta-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]",
            ),
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
            cls="bg-gray-800 rounded-lg p-3 md:p-6 shadow-xl",
        ),


        ft.Script("""
            (function(){
              var leadersBtn = document.getElementById('detail-toggle-leaders');
              var colorsBtn = document.getElementById('detail-toggle-colors');
              var viewInput = document.getElementById('detail-view-mode-input');
              if (!leadersBtn || !colorsBtn || !viewInput) return;
              function activate(isLeaders){
                viewInput.value = isLeaders ? 'leaders' : 'colors';
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
              activate(true);
              leadersBtn.addEventListener('click', function(){ activate(true); });
              colorsBtn.addEventListener('click', function(){ activate(false); });
            })();
        """),

        ft.Script("""
            (function(){
              var leadersBtn = document.getElementById('meta-toggle-leaders');
              var colorsBtn = document.getElementById('meta-toggle-colors');
              var viewInput = document.getElementById('meta-view-mode-input');
              if (!leadersBtn || !colorsBtn || !viewInput) return;
              function activate(isLeaders){
                viewInput.value = isLeaders ? 'leaders' : 'colors';
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
              activate(true);
              leadersBtn.addEventListener('click', function(){ activate(true); });
              colorsBtn.addEventListener('click', function(){ activate(false); });
            })();
        """),

        # Hidden container: synced meta_format inputs derived from the range slider
        ft.Div(
            *default_meta_format_inputs,
            id="meta-format-hidden-container",
            style="display:none;",
        ),
        # JS: keep hidden meta_format inputs in sync with the range slider and notify charts
        ft.Script("""
            (function(){
                var sliderEl = document.getElementById('meta-format-slider');
                if (!sliderEl) return;
                var allMetas = JSON.parse(sliderEl.dataset.labels || '[]');
                var container = document.getElementById('meta-format-hidden-container');
                if (!container) return;

                function updateMetaFormats() {
                    var toInput = document.querySelector("[name='to_meta_idx']");
                    if (!toInput) return;
                    var toIdx = parseInt(toInput.value);
                    var meta = allMetas[toIdx];
                    container.innerHTML = '';
                    var inp = document.createElement('input');
                    inp.type = 'hidden';
                    inp.name = 'meta_format';
                    inp.value = meta;
                    container.appendChild(inp);
                    var tooltipEl = document.getElementById('meta-bubble-chart-tooltip');
                    if (tooltipEl) tooltipEl.setAttribute('data-tooltip', 'Meta Format: ' + meta + '. Size of the bubbles increases with the tournament wins');
                    document.body.dispatchEvent(new Event('metaRangeChanged'));
                }

                var fromInput = document.querySelector("[name='from_meta_idx']");
                var toInput = document.querySelector("[name='to_meta_idx']");
                if (fromInput) fromInput.addEventListener('change', updateMetaFormats);
                if (toInput) toInput.addEventListener('change', updateMetaFormats);
            })();
        """),

        # Divider
        ft.Br(),

        # Tournament charts section
        ft.Div(
            ft.Div(
                ft.H2("Decklist & Leader Popularity", cls="text-2xl font-bold text-white"),
                ft.P(
                    "Popularity charts for the most recent meta format in the selected range.",
                    cls="text-gray-400 text-sm mt-1",
                ),
                cls="mb-6",
            ),
            ft.Div(
                ft.Div(create_decklist_popularity_section(id_prefix="meta-", extra_triggers="metaRangeChanged from:body, change from:#region-select"), cls="w-full"),
                ft.Div(create_leader_popularity_section(id_prefix="meta-", extra_triggers="metaRangeChanged from:body, change from:#region-select", data_tooltip=data_tooltip_bubble_chart), cls="w-full"),
                cls="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 lg:gap-8 w-full",
            ),
            cls="w-full",
        ),
        cls="min-h-screen p-4 md:p-6 max-w-7xl mx-auto w-full",
    )
