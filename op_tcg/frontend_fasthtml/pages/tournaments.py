from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion

SELECT_CLS = "bg-gray-700 text-white p-2 rounded"
HX_INCLUDE = "[name='meta_format'],[name='region']"

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
        hx_get="/api/tournaments/chart",
        hx_trigger="change",
        hx_target="#tournament-chart-container",
        hx_include=HX_INCLUDE
    )

    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=(r == MetaFormatRegion.ALL)) for r in regions],
        hx_get="/api/tournaments/chart",
        hx_trigger="change",
        hx_target="#tournament-chart-container",
        hx_include=HX_INCLUDE
    )

    return ft.Div(
        meta_format_select,
        region_select,
        cls="space-y-4"
    )

def tournaments_page():
    return ft.Div(
        # Header and Filters Section
        ft.Div(
            ft.H1("Tournament Statistics", cls="text-3xl font-bold text-white"),
            cls="mb-8"
        ),
        
        # Chart Container
        ft.Div(
            id="tournament-chart-container",
            hx_get="/api/tournaments/chart",
            hx_trigger="load",
            hx_include=HX_INCLUDE,
            cls="mt-8"
        ),
        
        cls="min-h-screen p-6 max-w-7xl mx-auto"
    ) 