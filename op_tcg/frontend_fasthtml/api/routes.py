from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table
from op_tcg.frontend_fasthtml.utils.launch import init_load_data
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart

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

    @rt("/api/leader-chart/{leader_id}")
    def leader_chart(request: Request, leader_id: str):
        all_meta_formats = MetaFormat.to_list()
        meta_format = MetaFormat(request.query_params.get("meta_format", MetaFormat.latest_meta_format))
        meta_format_index = all_meta_formats.index(meta_format)
        latest_meta_format_index = all_meta_formats.index(MetaFormat.latest_meta_format())

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
        
        # Prepare data for the chart, including null values for missing meta formats
        chart_data = []
        for meta_format in meta_formats_between[-5-(latest_meta_format_index-meta_format_index):meta_format_index]:
            if meta_format in meta_to_leader:
                leader = meta_to_leader[meta_format]
                chart_data.append({
                    "meta": str(meta_format),
                    "winRate": round(leader.win_rate * 100, 2),
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
        win_rate_values = [d["winRate"] for d in chart_data if d["winRate"] is not None]
        color = ChartColors.POSITIVE if len(win_rate_values) < 2 or (len(win_rate_values) >= 2 and win_rate_values[-1] > win_rate_values[-2]) else ChartColors.NEGATIVE

        return create_line_chart(
            container_id=f"chart-container-{leader_id}",
            data=chart_data,
            color=color,
            show_x_axis=False,
            show_y_axis=False
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