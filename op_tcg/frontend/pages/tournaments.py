from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend.components.loading import create_loading_spinner, create_loading_overlay
from op_tcg.frontend.components.tournament_charts import (
    create_decklist_popularity_section,
    create_leader_popularity_section,
)

SELECT_CLS = "bg-gray-700 text-white p-2 rounded"
FILTER_HX_ATTRS = {
    "hx_get": "/api/tournament-content",
    "hx_trigger": "change",
    "hx_target": "#tournament-content",
    "hx_include": "[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']"
}

def create_filter_components(selected_meta_formats=None, selected_region: MetaFormatRegion | None = None):
    latest_meta = MetaFormat.latest_meta_format()
    
    # If no selected formats provided, default to latest
    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]
    
    # Default region
    selected_region = selected_region or MetaFormatRegion.ALL

    # Release meta formats multi-select - use region for filtering available formats
    meta_format_select = ft.Select(
        label="Meta Formats",
        id="meta-formats-select",
        name="meta_format",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(mf, value=mf, selected=(mf in selected_meta_formats)) for mf in reversed(MetaFormat.to_list(region=MetaFormatRegion.ALL))],
        **FILTER_HX_ATTRS
    )

    regions = MetaFormatRegion.to_list()
    region_select = ft.Select(
        label="Region",
        id="region-select",
        name="region",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(r, value=r, selected=(r == selected_region)) for r in regions],
        **FILTER_HX_ATTRS
    )

    return ft.Div(
        meta_format_select,
        region_select,
        cls="space-y-4"
    )

def create_tournament_content():
    return ft.Div(
        # Add style to prevent horizontal overflow on mobile
        ft.Style("""
            /* Prevent horizontal overflow on mobile */
            html, body {
                overflow-x: hidden !important;
                max-width: 100vw !important;
            }
            
            /* Ensure all chart containers stay within bounds */
            .bg-gray-800\\/30, .bg-gray-900\\/50 {
                max-width: 100%;
                overflow-x: hidden;
            }
            
            /* Ensure tooltips don't cause overflow */
            #chartjs-tooltip {
                max-width: 90vw !important;
                box-sizing: border-box !important;
            }
        """),
        # Header and Filters Section
        ft.Div(
            ft.H1("Tournaments", cls="text-3xl font-bold text-white"),
            cls="mb-8"
        ),

        # Analytics Dashboard Section - Mobile-optimized layout
        ft.Div(
            ft.H2("Tournament Analytics", cls="text-2xl md:text-3xl font-bold text-white mb-6 md:mb-8 text-center px-2"),
            
            # Chart Grid Container - Mobile-first responsive design
            ft.Div(
                # Decklist Popularity Section
                ft.Div(
                    create_decklist_popularity_section(id_prefix="tournament-"),
                    cls="w-full"
                ),

                # Tournament Leader Popularity Section
                ft.Div(
                    create_leader_popularity_section(id_prefix="tournament-"),
                    cls="w-full"
                ),
                
                cls="grid grid-cols-1 lg:grid-cols-2 gap-4 md:gap-6 lg:gap-8 w-full"
            ),
            cls="mt-6 md:mt-8 w-full"
        ),
        
        # Tournament List Section
        ft.Div(
            ft.Div(
                ft.H2("Tournament Explorer", cls="text-2xl md:text-3xl font-bold text-white mb-6 md:mb-8 text-center px-2"),
                ft.Div(
                    # Loading overlay positioned absolutely within the list container
                    create_loading_overlay(
                        id="tournament-list-loading",
                        size="w-8 h-8"
                    ),
                    ft.Div(
                        id="tournament-list-container",
                        hx_get="/api/tournaments/all",
                        hx_trigger="load",
                        hx_include="[name='meta_format'],[name='region'],[name='min_matches'],[name='max_matches']",
                        hx_indicator="#tournament-list-loading",
                        cls="w-full h-full"
                    ),
                    cls="relative bg-gray-900/50 rounded-lg p-3 md:p-6 overflow-x-auto",
                    style="min-height: 200px;"
                ),
                cls="bg-gray-800 rounded-lg p-4 md:p-8 shadow-xl"
            ),
            cls="mt-8 md:mt-16"
        ),
        
        cls="min-h-screen p-3 md:p-6 max-w-7xl mx-auto w-full",
        id="tournament-content"
    )

def tournaments_page():
    return ft.Div(
        create_tournament_content()
    ) 