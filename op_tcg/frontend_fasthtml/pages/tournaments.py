from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner

SELECT_CLS = "bg-gray-700 text-white p-2 rounded"
FILTER_HX_ATTRS = {
    "hx_get": "/api/tournament-content",
    "hx_trigger": "change",
    "hx_target": "#tournament-content",
    "hx_include": "[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
    "hx_indicator": "#tournament-loading-indicator"
}

def create_filter_components(selected_meta_formats=None):
    latest_meta = MetaFormat.latest_meta_format()
    
    # If no selected formats provided, default to latest
    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]

    # Release meta formats multi-select
    meta_format_select = ft.Select(
        label="Meta Formats",
        id="meta-formats-select",
        name="meta_format",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats)) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS
    )

    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=(r == MetaFormatRegion.ALL)) for r in regions],
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
            ft.H1("Tournament Statistics", cls="text-3xl font-bold text-white"),
            cls="mb-8"
        ),

        # Loading Spinner
        create_loading_spinner(
            id="tournament-loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),

        # Chart Container
        ft.Div(
            id="tournament-chart-container",
            hx_get="/api/tournaments/chart",
            hx_trigger="load",
            hx_indicator="#tournament-loading-indicator",
            hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
            cls="mt-8"
        ),
        
        # Tournament List Section
        ft.Div(
            ft.H2("Tournament List", cls="text-2xl font-bold text-white mb-6"),
            ft.Div(
                id="tournament-list-container",
                hx_get="/api/tournaments/all",
                hx_trigger="load",
                hx_indicator="#tournament-loading-indicator",
                hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
            ),
            cls="mt-32"
        ),
        
        cls="min-h-screen p-6 max-w-7xl mx-auto",
        id="tournament-content"
    )

def tournaments_page():
    return ft.Div(
        create_tournament_content()
    ) 