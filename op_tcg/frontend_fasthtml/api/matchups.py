from fasthtml import ft
from starlette.requests import Request
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.leader_matchups import get_best_worst_matchups
from op_tcg.frontend_fasthtml.components.matchup import create_matchup_analysis
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart, create_bar_chart
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams
from op_tcg.frontend_fasthtml.pages.leader import HX_INCLUDE

def setup_api_routes(rt):
    @rt("/api/leader-matchups")
    async def get_leader_matchups(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get best and worst matchups
        matchups = get_best_worst_matchups(params.lid, params.meta_format)
        
        # Get leader data
        leader_data = next(iter(get_leader_extended(leader_ids=[params.lid])), None)
        
        if not leader_data:
            return ft.P("No data available for this leader.", cls="text-red-400")
            
        # Create and return the matchup analysis component
        return create_matchup_analysis(
            leader_data=leader_data,
            matchups=matchups,
            hx_include=HX_INCLUDE
        )

    @rt("/api/leader-matchup-details")
    async def get_leader_matchup_details(request: Request):
        """Get details for a specific matchup.
        Details include (best or worst opponent):
        - Image with hyperlink
        - Win rate chart
        - Match count chart
        """
        params = LeaderDataParams(**get_query_params_as_dict(request))
        meta_format = params.meta_format[0]
        
        # Check which matchup we're looking at (best or worst)
        matchup_type = next((key.split('_')[1] for key in params.keys() if key.startswith('lid_')), None)
        if not matchup_type:
            return ft.P("Invalid matchup type", cls="text-red-400")
            
        # Get the selected leader ID
        leader_id = params[f'lid_{matchup_type}']
        if not leader_id:
            return ft.P("No leader selected", cls="text-gray-400")
            
        # Get leader data
        leader_data = next(iter(get_leader_extended(leader_ids=[leader_id])), None)
        if not leader_data:
            return ft.P("No data available for this leader", cls="text-red-400")
            
        # Get matchup data
        matchups = get_best_worst_matchups(params.lid, params.meta_format)
        if not matchups:
            return ft.P("No matchup data available", cls="text-gray-400")
            
        # Find the specific matchup
        matchup = None
        if matchup_type == 'best':
            matchup = next((m for m in matchups.easiest_matchups if m.leader_id == leader_id), None)
        else:
            matchup = next((m for m in matchups.hardest_matchups if m.leader_id == leader_id), None)
            
        if not matchup:
            return ft.P("No matchup data available for this leader", cls="text-gray-400")
            
        # Create chart data
        chart_data = [
            {"meta": str(meta), "winRate": round(wr * 100, 2)}
            for meta, wr in matchup.win_rate_chart_data.items()
        ]
        chart_data.sort(key=lambda x: x["meta"])
        
        # Create match count data
        match_data = [
            {"meta": str(meta), "matches": matchup.total_matches}
            for meta in matchup.meta_formats
        ]
        match_data.sort(key=lambda x: x["meta"])
        
        # Create the matchup details view
        return ft.Div(
            # Image with hyperlink
            ft.A(
                ft.Img(
                    src=leader_data.aa_image_url,
                    cls="w-full rounded-lg shadow-lg mb-2"
                ),
                href=f"/leader?lid={leader_id}",
                hx_include=params.hx_include if hasattr(params, 'hx_include') else None,
            ),
            # Win rate chart
            ft.Div(
                create_line_chart(
                    container_id=f"win-rate-chart-{leader_id}",
                    data=chart_data,
                    color=ChartColors.POSITIVE if matchup_type == "best" else ChartColors.NEGATIVE,
                    show_x_axis=True,
                    show_y_axis=True
                ),
                cls="mb-4"
            ),
            # Match count chart
            ft.Div(
                create_bar_chart(
                    container_id=f"match-count-chart-{leader_id}",
                    data=match_data,
                    show_x_axis=True,
                    show_y_axis=True
                ),
                cls="h-[120px] w-full"
            ),
            cls="w-full"
        ) 