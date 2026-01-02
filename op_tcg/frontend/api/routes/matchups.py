from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.leader_matchups import get_best_worst_matchups, get_opponent_win_rate_chart, get_all_leader_matchups
from op_tcg.frontend.components.matchup import create_matchup_analysis, create_matchup_card
from op_tcg.frontend.utils.extract import get_leader_extended, get_leader_win_rate
from op_tcg.frontend.utils.charts import create_line_chart, create_bar_chart, create_leader_win_rate_radar_chart
from op_tcg.frontend.utils.colors import ChartColors
from op_tcg.frontend.pages.leader import HX_INCLUDE
from op_tcg.frontend.pages.matchups import create_filter_components, create_matchup_content
from op_tcg.frontend.api.models import LeaderDataParams, MatchupParams
from op_tcg.frontend.utils.win_rate import get_radar_chart_data
from op_tcg.frontend.utils.table import create_leader_image_cell, create_win_rate_cell
from typing import Dict, List, Tuple, Set

def setup_api_routes(rt):
    @rt("/api/leader-matchups")
    async def get_leader_matchups(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get all matchups
        all_matchups = get_all_leader_matchups(params.lid, params.meta_format, min_matches=params.min_matches, only_official=params.only_official)

        # Get leader data
        leader_data = next(iter(get_leader_extended(leader_ids=[params.lid])), None)
        
        if not leader_data:
            return ft.P("No data available for this leader.", cls="text-red-400")

        # Create OpponentMatchups object
        from op_tcg.frontend.api.models import OpponentMatchups
        matchups = None
        matchup_cards = None

        if all_matchups:
            matchups = OpponentMatchups(
                easiest_matchups=all_matchups[:10],
                hardest_matchups=sorted(all_matchups, key=lambda x: x.win_rate)[:10]
            )

            # Get opponent data for cards
            opponent_ids = [m.leader_id for m in all_matchups]
            opponent_data = get_leader_extended(leader_ids=opponent_ids)
            opponent_dict = {l.id: l for l in opponent_data}

            # Create cards
            matchup_cards = []
            for m in all_matchups:
                opponent = opponent_dict.get(m.leader_id)
                if not opponent:
                    continue
                matchup_cards.append(create_matchup_card(opponent, m, params.meta_format, params.region))

        # Create and return the matchup analysis component
        return create_matchup_analysis(
            leader_data=leader_data,
            matchups=matchups,
            hx_include=HX_INCLUDE,
            min_matches=params.min_matches,
            matchup_cards=matchup_cards
        )

    @rt("/api/leader-matchups-list")
    async def get_leader_matchups_list(request: Request):
        """Get all matchups for a leader in a horizontal list format."""
        # Parse params using Pydantic model
        params_dict = get_query_params_as_dict(request)
        params = LeaderDataParams(**params_dict)

        # Get min_matches from params, default to 4
        try:
            min_matches = int(params_dict.get('min_matches', 4))
        except ValueError:
            min_matches = 4

        # Get all matchups
        matchups = get_all_leader_matchups(params.lid, params.meta_format, min_matches=min_matches, only_official=params.only_official)

        if not matchups:
            return ft.P("No matchup data available for this criteria.", cls="text-gray-400 p-4")

        # Get leader data for opponents to display images/names
        opponent_ids = [m.leader_id for m in matchups]
        opponent_data = get_leader_extended(leader_ids=opponent_ids)
        opponent_dict = {l.id: l for l in opponent_data}

        # Create cards
        cards = []
        for m in matchups:
            opponent = opponent_dict.get(m.leader_id)
            if not opponent:
                continue
            cards.append(create_matchup_card(opponent, m, params.meta_format, params.region))

        return ft.Div(
            *cards,
            cls="flex flex-row gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
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
                href=f"/leader?lid={leader_id}{''.join([f'&meta_format={mf}' for mf in params.meta_format])}{f'&region={params.region}' if params.region else ''}",
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
                cls="mb-4",
                style="height: 120px;"
            ),
            # Match count chart
            ft.Div(
                create_bar_chart(
                    container_id=f"match-count-chart-{leader_id}",
                    data=match_data,
                    show_x_axis=True,
                    show_y_axis=True
                ),
                cls="mb-4",
                style="height: 120px;"
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

        # Create and return the radar chart with responsive container
        return ft.Div(
            create_leader_win_rate_radar_chart(
                container_id="matchup-radar-chart",
                data=radar_data,
                leader_ids=params.leader_ids,
                colors=colors
            ),
            cls="w-full h-[500px] md:h-[600px]"  # Increased height, responsive
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

        # Create data structure for win rates
        matchup_data = []
        for wr in win_rate_data:
            if wr.leader_id in params.leader_ids and wr.opponent_id in params.leader_ids:
                matchup_data.append({
                    'leader_id': wr.leader_id,
                    'opponent_id': wr.opponent_id,
                    'win_rate': round(wr.win_rate * 100, 1),
                    'total_matches': wr.total_matches
                })

        # Calculate overall win rates for each leader
        leader_overall_wr = {}
        for leader_id in params.leader_ids:
            leader_matches = [m for m in matchup_data if m['leader_id'] == leader_id]
            if leader_matches:
                total_matches = sum(m['total_matches'] for m in leader_matches)
                weighted_wr = sum(m['win_rate'] * m['total_matches'] for m in leader_matches) / total_matches
                leader_overall_wr[leader_id] = round(weighted_wr, 1)
            else:
                leader_overall_wr[leader_id] = 0.0

        # Sort leaders by win rate
        sorted_leader_ids = sorted(leader_overall_wr.keys(), key=lambda x: leader_overall_wr[x], reverse=True)

        # Create win rate lookup dictionary
        win_rate_lookup = {
            (m['leader_id'], m['opponent_id']): (m['win_rate'], m['total_matches'])
            for m in matchup_data
        }

        # Create header cells
        header_cells = [
            ft.Th(
                ft.Div(
                    ft.Span("Opponent →", cls="block text-left"),
                    ft.Span("Leader ↓", cls="block text-left"),
                    cls="flex flex-col w-full"
                ),
                cls="text-left py-2 px-4 w-[200px]"
            ),
            ft.Th(
                ft.Div(
                    ft.Span("Overall"),
                    ft.Br(),
                    ft.Span("Win Rate")
                ),
                cls="text-left py-2 px-4 w-[120px]"
            )
        ]
        
        # Add leader columns to header
        for leader_id in sorted_leader_ids:
            if leader_id in leader_dict:
                leader = leader_dict[leader_id]
                header_cells.append(
                    ft.Th(
                        ft.Div(
                            create_leader_image_cell(
                                image_url=leader.image_url,
                                name=f"{leader.name}\n({leader.get_color_short_name()})",
                                color=leader.to_hex_color(),
                                horizontal=False
                            ),
                            cls="w-[120px]"  # Fixed width for matchup columns
                        ),
                        cls="p-0"
                    )
                )

        # Create table rows
        rows = []
        for leader_id in sorted_leader_ids:
            if leader_id in leader_dict:
                leader = leader_dict[leader_id]
                row_cells = [
                    # Leader image cell
                    ft.Td(
                        ft.Div(
                            create_leader_image_cell(
                                image_url=leader.aa_image_url,
                                name=f"{leader.name}\n({leader.get_color_short_name()})",
                                color=leader.to_hex_color()
                            ),
                            cls="w-[200px]"  # Fixed width for leader column
                        ),
                        cls="p-0"
                    ),
                    # Overall win rate cell
                    create_win_rate_cell(
                        win_rate=leader_overall_wr[leader_id],
                        tooltip=f"Overall Win Rate"
                    )
                ]
                
                # Add matchup cells
                for opponent_id in sorted_leader_ids:
                    if opponent_id in leader_dict:
                        if leader_id == opponent_id:
                            win_rate = 50.0
                            total_matches = 0
                        else:
                            win_rate, total_matches = win_rate_lookup.get((leader_id, opponent_id), (None, 0))
                            
                        row_cells.append(
                            create_win_rate_cell(
                                win_rate=win_rate,
                                tooltip=f"Match Count: {int(total_matches)}"
                            )
                        )
                rows.append(ft.Tr(*row_cells, cls="hover:bg-gray-700"))

        if not rows:
            return ft.P("No matchup data available for the selected leaders", cls="text-red-400")

        # Return the complete table with a container for proper styling
        return ft.Div(
            ft.Div(
                ft.Table(
                    ft.Thead(
                        ft.Tr(*header_cells, cls="bg-gray-800"),
                        cls="text-white"
                    ),
                    ft.Tbody(
                        *rows,
                        cls="text-gray-300"
                    ),
                    cls="w-full text-left border-collapse"
                ),
                cls="min-w-[1024px] w-full"  # Inner container with minimum width
            ),
            cls="overflow-x-auto w-full"  # Outer container with scroll
        ) 