from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended, get_leader_win_rate

SELECT_CLS = "bg-gray-700 text-white p-2 rounded"
FILTER_HX_ATTRS = {
    "hx_get": "/api/matchup-content",
    "hx_trigger": "change",
    "hx_target": "#matchup-content",
    "hx_include": "[name='meta_format'],[name='only_official'],[name='leader_ids']",
    "hx_indicator": "#matchup-loading-indicator"
}

def create_filter_components(selected_meta_formats=None, selected_leader_ids=None, only_official=True):
    latest_meta = MetaFormat.latest_meta_format()
    
    # If no selected formats provided, default to latest
    if not selected_meta_formats:
        selected_meta_formats = [latest_meta]

    # Get available leaders and win rate data
    leader_data = get_leader_extended()
    win_rate_data = get_leader_win_rate(meta_formats=selected_meta_formats)
    
    # Filter leaders by meta format and official status
    filtered_win_rate_data = [wr for wr in win_rate_data if wr.only_official == only_official]
    leader_data = [l for l in leader_data if l.meta_format in selected_meta_formats]
    
    # Filter leaders that have matches in the filtered win rate data
    leaders_with_matches = {wr.leader_id for wr in filtered_win_rate_data}
    leader_data = [l for l in leader_data if l.id in leaders_with_matches]
    
    # Sort by d_score and get unique leaders
    leader_data.sort(key=lambda x: (x.d_score if x.d_score is not None else 0), reverse=True)
    seen_leader_ids = set()
    unique_leader_data = []
    for leader in leader_data:
        if leader.id not in seen_leader_ids:
            seen_leader_ids.add(leader.id)
            unique_leader_data.append(leader)
    
    # If no selected leaders provided, use top 5 by d_score
    if not selected_leader_ids and unique_leader_data:
        selected_leader_ids = [l.id for l in unique_leader_data[:5]]

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

    # Only official toggle
    only_official_toggle = ft.Div(
        ft.Label(
            "Only Official Tournaments",
            htmlFor="only-official-toggle",
            cls="block text-sm font-medium text-gray-300 mb-1"
        ),
        ft.Input(
            type="checkbox",
            id="only-official-toggle",
            name="only_official",
            checked=only_official,
            cls="form-checkbox h-5 w-5 text-blue-600 bg-gray-700 border-gray-500 rounded focus:ring-blue-500",
            **FILTER_HX_ATTRS
        ),
        cls="flex items-center space-x-2"
    )

    # Leader multiselect
    leader_select = ft.Select(
        label="Leaders",
        id="leader-select",
        name="leader_ids",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[
            ft.Option(
                f"{leader.name} ({leader.get_color_short_name()})", 
                value=leader.id,
                selected=(leader.id in (selected_leader_ids or []))
            ) 
            for leader in unique_leader_data
        ],
        **FILTER_HX_ATTRS
    )

    return ft.Div(
        meta_format_select,
        only_official_toggle,
        leader_select,
        cls="space-y-4"
    )

def create_matchup_content(selected_meta_formats=None, selected_leader_ids=None, only_official=True):
    return ft.Div(
        # Header and Filters Section
        ft.Div(
            ft.H1("Leader Matchups", cls="text-3xl font-bold text-white"),
            cls="mb-8"
        ),

        # Loading Spinner
        create_loading_spinner(
            id="matchup-loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),

        # Matchup Content Container
        ft.Div(
            id="matchup-chart-container",
            hx_get="/api/matchups/chart",
            hx_trigger="load",
            hx_indicator="#matchup-loading-indicator",
            hx_include=FILTER_HX_ATTRS["hx_include"],
            cls="mt-8 w-full overflow-hidden"
        ),
        
        # Matchup Table Section
        ft.Div(
            ft.H2("Matchup Details", cls="text-2xl font-bold text-white mb-6"),
            ft.Div(
                ft.Div(
                    id="matchup-table-container",
                    hx_get="/api/matchups/table",
                    hx_trigger="load",
                    hx_indicator="#matchup-loading-indicator",
                    hx_include=FILTER_HX_ATTRS["hx_include"],
                ),
                cls="w-full overflow-x-auto"
            ),
            cls="mt-8 w-full"
        ),
        
        cls="min-h-screen p-4 md:p-6 w-full",
        id="matchup-content"
    )

def matchups_page():
    return ft.Div(
        create_matchup_content()
    ) 