from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.leader_matchups import get_best_worst_matchups, get_opponent_win_rate_chart
from op_tcg.frontend_fasthtml.components.matchup import create_matchup_analysis
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended, get_leader_win_rate
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart, create_bar_chart, create_leader_win_rate_radar_chart
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.pages.leader import HX_INCLUDE
from op_tcg.frontend_fasthtml.pages.matchups import create_filter_components, create_matchup_content
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams, MatchupParams
from op_tcg.frontend_fasthtml.utils.win_rate import get_radar_chart_data

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
        """Get details for a specific matchup."""
        params_dict = get_query_params_as_dict(request)
        params = LeaderDataParams(**params_dict)
        chart_meta_formats = MetaFormat.to_list(until_meta_format=params.meta_format[0])
        
        # Check which matchup we're looking at (best or worst)
        matchup_type = next((key.split('_')[1] for key in params_dict.keys() if key.startswith('lid_')), None)
        if not matchup_type:
            return ft.P("Invalid matchup type", cls="text-red-400")
            
        # Get the selected leader ID
        leader_id = params_dict[f'lid_{matchup_type}']
        if not leader_id:
            return ft.P("No leader selected", cls="text-gray-400")
            
        # Get leader data
        leader_data = next(iter(get_leader_extended(leader_ids=[leader_id])), None)
        if not leader_data:
            return ft.P("No data available for this leader", cls="text-red-400")
            
        # Get matchup data
        chart_data, match_data = get_opponent_win_rate_chart(params.lid, leader_id, chart_meta_formats)
        
        if not chart_data:
            return ft.P("No matchup data available for this leader", cls="text-gray-400")
            
        # Create chart data
        chart_data = [
            {"meta": str(meta), "winRate": round(wr * 100, 2)}
            for meta, wr in chart_data.items()
        ]
        chart_data.sort(key=lambda x: x["meta"])
        
        # Create match count data
        match_data = [
            {"meta": str(meta), "matches": total_matches}
            for meta, total_matches in match_data.items()
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

    @rt("/api/matchup-content")
    def get_matchup_content(request: Request):
        """Return the matchup page content with updated filters."""
        params_dict = get_query_params_as_dict(request)
        
        # Parse params using Pydantic model
        params = MatchupParams(**params_dict)
        
        # Create filter components with current selections
        return create_matchup_content(
            selected_meta_formats=params.meta_format,
            selected_leader_ids=params.leader_ids,
            only_official=params.only_official
        )

    @rt("/api/matchups/chart")
    def get_matchup_chart(request: Request):
        """Return the matchup radar chart."""
        # Parse params using Pydantic model
        params = MatchupParams(**get_query_params_as_dict(request))

        if not params.leader_ids:
            return ft.P("Please select at least one leader", cls="text-gray-400")

        # Get leader data
        leader_data = get_leader_extended()
        leader_data = [l for l in leader_data if l.meta_format in params.meta_format]
        leader_dict = {l.id: l for l in leader_data}
        
        # Get radar chart data using the win_rate.py function
        radar_data = get_radar_chart_data(
            leader_ids=params.leader_ids,
            meta_formats=params.meta_format,
            only_official=params.only_official
        )

        if not radar_data:
            return ft.P("No matchup data available for the selected leaders", cls="text-red-400")

        # Get colors for each leader
        colors = [leader_dict[lid].to_hex_color() for lid in params.leader_ids if lid in leader_dict]

        # Create and return the radar chart
        return create_leader_win_rate_radar_chart(
            container_id="matchup-radar-chart",
            data=radar_data,
            leader_ids=params.leader_ids,
            colors=colors
        )

    @rt("/api/matchups/table")
    def get_matchup_table(request: Request):
        """Return the matchup details table."""
        # Parse params using Pydantic model
        params = MatchupParams(**get_query_params_as_dict(request))

        if not params.leader_ids:
            return ft.P("Please select at least one leader", cls="text-gray-400")

        # Get leader data
        leader_data = get_leader_extended()
        leader_data = [l for l in leader_data if l.meta_format in params.meta_format]
        leader_dict = {l.id: l for l in leader_data}
        
        # Get win rate data
        win_rate_data = get_leader_win_rate(meta_formats=params.meta_format)
        win_rate_data = [wr for wr in win_rate_data if wr.only_official == params.only_official]

        if not win_rate_data:
            return ft.P("No matchup data available for the selected criteria", cls="text-red-400")

        # Create table header
        header_cells = [
            ft.Th("Leader", cls="text-left py-2 px-4"),
            ft.Th("Win Rate", cls="text-left py-2 px-4"),
            ft.Th("Total Matches", cls="text-left py-2 px-4")
        ]

        # Create table rows
        rows = []
        for leader_id in params.leader_ids:
            if leader_id in leader_dict:
                leader = leader_dict[leader_id]
                leader_win_rates = [wr for wr in win_rate_data if wr.leader_id == leader_id]
                if leader_win_rates:
                    avg_win_rate = sum(wr.win_rate for wr in leader_win_rates) / len(leader_win_rates)
                    total_matches = sum(wr.total_matches for wr in leader_win_rates)
                    
                    rows.append(
                        ft.Tr(
                            ft.Td(
                                ft.Div(
                                    ft.Img(
                                        src=leader.image_url,
                                        cls="w-8 h-8 rounded-full mr-2"
                                    ),
                                    ft.Span(leader.name),
                                    cls="flex items-center"
                                ),
                                cls="py-2 px-4"
                            ),
                            ft.Td(
                                f"{avg_win_rate:.1%}",
                                cls="py-2 px-4"
                            ),
                            ft.Td(
                                str(total_matches),
                                cls="py-2 px-4"
                            ),
                            cls="hover:bg-gray-700"
                        )
                    )

        if not rows:
            return ft.P("No matchup data available for the selected leaders", cls="text-red-400")

        # Return the complete table
        return ft.Table(
            ft.Thead(
                ft.Tr(*header_cells, cls="bg-gray-800"),
                cls="text-white"
            ),
            ft.Tbody(
                *rows,
                cls="text-gray-300"
            ),
            cls="w-full text-left border-collapse"
        ) 