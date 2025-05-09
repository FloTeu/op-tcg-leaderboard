from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table
from op_tcg.frontend_fasthtml.utils.launch import init_load_data
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart, create_leader_win_rate_radar_chart
from op_tcg.frontend_fasthtml.utils.win_rate import get_radar_chart_data
from op_tcg.frontend_fasthtml.pages.leader import create_leader_select, create_leader_content

DATA_IS_LOADED = False

def get_filtered_leaders(request: Request):
    max_max_match_count = 10000
    # Get query parameters from request
    meta_format = MetaFormat(request.query_params.get("meta_format", MetaFormat.latest_meta_format))
    release_meta_formats = request.query_params.getlist("release_meta_formats")
    region = MetaFormatRegion(request.query_params.get("region", MetaFormatRegion.ALL))
    only_official = request.query_params.get("only_official", "true").lower() == "true"
    min_match_count = int(request.query_params.get("min_matches", 0))
    max_match_count = int(request.query_params.get("max_matches", max_max_match_count))
    
    # Get leader extended data
    leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=region)
    
    # Apply filters
    return filter_leader_extended(
        leaders=leader_extended_data,
        only_official=only_official,
        release_meta_formats=release_meta_formats if release_meta_formats else None,
        match_count_min=min_match_count if min_match_count else None,
        match_count_max=max_match_count if max_match_count != max_max_match_count else None
    )

def setup_api_routes(rt):
    @rt("/api/launch")
    def launch_data(request: Request):
        global DATA_IS_LOADED
        if not DATA_IS_LOADED:
            init_load_data()
            DATA_IS_LOADED = True
        return {"data_is_loaded": DATA_IS_LOADED}

    @rt("/api/leader-select")
    def get_leader_select(request: Request):
        # Get selected meta formats from request
        meta_formats = request.query_params.getlist("meta_format")
        leader_id = request.query_params.get("lid")
        
        if not meta_formats:
            meta_formats = [MetaFormat.latest_meta_format()]
        else:
            # Convert string values to MetaFormat enum
            meta_formats = [MetaFormat(mf) for mf in meta_formats]
        
        # Create and return the updated leader select
        return create_leader_select(meta_formats, leader_id)

    @rt("/api/leader-chart/{leader_id}")
    def leader_chart(request: Request, leader_id: str):
        # Get query parameters
        all_meta_formats = MetaFormat.to_list()
        meta_format = MetaFormat(request.query_params.get("meta_format", MetaFormat.latest_meta_format()))
        meta_format_index = all_meta_formats.index(meta_format)
        latest_meta_format_index = all_meta_formats.index(MetaFormat.latest_meta_format())
        
        # Get the last_n parameter (default to 5)
        try:
            last_n = int(request.query_params.get("last_n", "5"))
        except ValueError:
            last_n = 5
        
        # Get color parameter (default to neutral for leader page)
        color_param = request.query_params.get("color", "neutral")
        
        # Get leader data for all meta formats
        filtered_leaders = get_filtered_leaders(request)
        
        # Sort by meta format to ensure chronological order
        filtered_leaders.sort(key=lambda x: all_meta_formats.index(x.meta_format))

        first_meta_format = filtered_leaders[0].meta_format if filtered_leaders else None
        
        leader_history = [l for l in filtered_leaders if l.id == leader_id]
        start_index = all_meta_formats.index(first_meta_format) if first_meta_format in all_meta_formats else 0
        meta_formats_between = all_meta_formats[start_index:]
        
        # Create a lookup for existing data points
        meta_to_leader = {l.meta_format: l for l in leader_history}
        
        # Determine range of meta formats to include based on last_n
        end_index = meta_format_index + 1 - start_index  # Exclusive end index
        start_index = max(0, end_index - last_n)  # Take at most last_n meta formats
        relevant_meta_formats = meta_formats_between[start_index:end_index]
        
        # Prepare data for the chart, including null values for missing meta formats
        chart_data = []
        for meta_format in relevant_meta_formats:
            if meta_format in meta_to_leader:
                leader = meta_to_leader[meta_format]
                chart_data.append({
                    "meta": str(meta_format),
                    "winRate": round(leader.win_rate * 100, 2) if leader.win_rate is not None else None,
                    "elo": leader.elo,
                    "matches": leader.total_matches
                })
            else:
                chart_data.append({
                    "meta": str(meta_format),
                    "winRate": None,
                    "elo": None,
                    "matches": None
                })
        
        # Determine chart color based on parameter or trend
        if color_param == "neutral":
            color = ChartColors.NEUTRAL
        else:
            # Default behavior: determine color based on win rate trend
            win_rate_values = [d["winRate"] for d in chart_data if d["winRate"] is not None]
            color = ChartColors.POSITIVE if len(win_rate_values) < 2 or (len(win_rate_values) >= 2 and win_rate_values[-1] > win_rate_values[-2]) else ChartColors.NEGATIVE

        # Create and return the chart
        return create_line_chart(
            container_id=f"win-rate-chart-{leader_id}",
            data=chart_data,
            color=color,
            show_x_axis=True,
            show_y_axis=True
        )

    @rt("/api/leaderboard")
    def api_leaderboard(request: Request):
        sort_by = LeaderboardSortBy(request.query_params.get("sort_by", LeaderboardSortBy.WIN_RATE))
        meta_format = MetaFormat(request.query_params.get("meta_format", MetaFormat.latest_meta_format))

        filtered_leaders = get_filtered_leaders(request)
        display_name2df_col_name = {
            "Name": "name",
            "Set": "id",
            LeaderboardSortBy.TOURNAMENT_WINS: "tournament_wins",
            LeaderboardSortBy.MATCH_COUNT: "total_matches",
            LeaderboardSortBy.WIN_RATE: "win_rate",
            LeaderboardSortBy.DOMINANCE_SCORE: "d_score",
            LeaderboardSortBy.ELO: "elo"
        }

        # Sort leaders by the specified sort criteria
        if sort_by == LeaderboardSortBy.TOURNAMENT_WINS:
            filtered_leaders.sort(key=lambda x: (x.tournament_wins > 0, x.tournament_wins, x.elo), reverse=True)
        else:
            filtered_leaders.sort(key=lambda x: getattr(x, display_name2df_col_name.get(sort_by)), reverse=True)
        
        # Create the leaderboard table
        return create_leaderboard_table(
            filtered_leaders,
            meta_format
        )

    @rt("/api/leader-data")
    async def get_leader_data(request: Request):
        # Get query parameters from request
        meta_formats = request.query_params.getlist("meta_format")
        if not meta_formats:
            meta_formats = [MetaFormat.latest_meta_format()]
        else:
            # Convert string values to MetaFormat enum if needed
            meta_formats = [MetaFormat(mf) if isinstance(mf, str) else mf for mf in meta_formats]
            
        leader_id = request.query_params.get("lid")
        only_official = request.query_params.get("only_official", "true").lower() == "true"
        
        # Get leader data
        if leader_id:
            # If a leader ID is provided, get data for that specific leader
            leader_data = get_leader_extended(leader_ids=[leader_id])
        else:
            # Otherwise, get all leaders and find the one with highest d_score
            leader_data = get_leader_extended()
            
        # Filter by meta format
        filtered_by_meta = [l for l in leader_data if l.meta_format in meta_formats]
        
        # Apply filters
        filtered_data = filter_leader_extended(
            leaders=filtered_by_meta,
            only_official=only_official
        )
        
        if not filtered_data:
            return ft.P("No data available for this leader.", cls="text-red-400")
            
        # If no specific leader was requested, find the one with highest d_score
        if not leader_id:
            # Sort by d_score and elo, handling None values
            def sort_key(leader):
                d_score = leader.d_score if leader.d_score is not None else 0
                elo = leader.elo if leader.elo is not None else 0
                return (-d_score, -elo)
            
            # Create unique leader mapping using only the most recent version from selected meta formats
            unique_leaders = {}
            for leader in filtered_data:
                if leader.id not in unique_leaders:
                    unique_leaders[leader.id] = leader
                else:
                    # If we already have this leader, keep the one from the most recent meta format
                    existing_meta_idx = MetaFormat.to_list().index(unique_leaders[leader.id].meta_format)
                    current_meta_idx = MetaFormat.to_list().index(leader.meta_format)
                    if current_meta_idx > existing_meta_idx:
                        unique_leaders[leader.id] = leader
            
            sorted_leaders = sorted(unique_leaders.values(), key=sort_key)
            if sorted_leaders:
                leader_data = sorted_leaders[0]
            else:
                return ft.P("No data available for leaders in the selected meta format.", cls="text-red-400")
        else:
            # If we have multiple versions of the same leader (from different meta formats),
            # use the most recent one
            if len(filtered_data) > 1:
                # Sort by meta format index (higher index = more recent)
                filtered_data.sort(key=lambda x: MetaFormat.to_list().index(x.meta_format), reverse=True)
            
            leader_data = next((l for l in filtered_data if l.id == leader_id), None)
            
            if not leader_data:
                return ft.P("No data available for this leader in the selected meta format.", cls="text-red-400")
        
        # Use the shared create_leader_content function
        return create_leader_content(leader_data)

    @rt("/api/leader-radar-chart")
    def leader_radar_chart(request: Request):
        leader_id = request.query_params.get("lid")
        
        # Get meta formats from request
        meta_formats = request.query_params.getlist("meta_format")
        if not meta_formats:
            meta_formats = [MetaFormat.latest_meta_format()]
        else:
            # Convert string values to MetaFormat enum
            meta_formats = [MetaFormat(mf) for mf in meta_formats]
            
        only_official = request.query_params.get("only_official", "true").lower() == "true"
        
        if not leader_id:
            return ft.Div(ft.P("No leader selected", cls="text-red-400"))
        
        # Get leader data to determine color
        leader_data = get_leader_extended(leader_ids=[leader_id])
        if not leader_data:
            return ft.Div(ft.P("Leader data not found", cls="text-red-400"))
            
        # Get filtered leader data
        leader = next((l for l in leader_data if l.meta_format in meta_formats), None)
        if not leader:
            return ft.Div(ft.P("Leader not found in selected meta format", cls="text-red-400"))
        
        # Get radar chart data
        radar_data = get_radar_chart_data([leader_id], meta_formats, only_official)
        if not radar_data:
            return ft.Div(ft.P("No matchup data available", cls="text-gray-400"))
        
        # Create a unique ID for this chart instance to avoid conflicts
        chart_id = f"radar-chart-{leader_id}-{hash(str(meta_formats))}"
        
        # Create radar chart
        return create_leader_win_rate_radar_chart(
            container_id=chart_id,
            data=radar_data,
            leader_ids=[leader_id],
            colors=[leader.to_hex_color()],
            show_legend=False,
        )