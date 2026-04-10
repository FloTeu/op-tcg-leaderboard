from fasthtml import ft

from op_tcg.backend.models.input import MetaFormatRegion
from op_tcg.frontend.components.loading import create_loading_spinner

SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

HX_INCLUDE = "[name='region']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/meta-share-chart",
    "hx_trigger": "change",
    "hx_target": "#meta-share-chart",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#meta-loading-indicator",
}


def create_filter_components(selected_region: MetaFormatRegion | None = None):
    selected_region = selected_region or MetaFormatRegion.ALL

    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=r == selected_region) for r in MetaFormatRegion.to_list()],
        **FILTER_HX_ATTRS,
    )

    return ft.Div(region_select, cls="space-y-4")


def meta_page():
    return ft.Div(
        ft.Div(
            ft.H1("Meta Analysis", cls="text-3xl font-bold text-white"),
            ft.P(
                "Leader play rates across meta formats. Only leaders with more than 5% meta share are shown.",
                cls="text-gray-300 mt-2",
            ),
            cls="mb-8",
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
        cls="min-h-screen p-4 md:p-6 w-full",
    )
