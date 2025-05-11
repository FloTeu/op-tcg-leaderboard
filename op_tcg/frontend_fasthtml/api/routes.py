from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table
from op_tcg.frontend_fasthtml.utils.launch import init_load_data
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict, get_filtered_leaders
from op_tcg.frontend_fasthtml.pages.leader import create_leader_select, create_leader_content
from op_tcg.frontend_fasthtml.api.charts import setup_api_routes as setup_charts_api_routes
from op_tcg.frontend_fasthtml.api.models import LeaderboardFilter, LeaderboardSort, LeaderSelectParams, LeaderDataParams
DATA_IS_LOADED = False


def setup_api_routes(rt):
    setup_charts_api_routes(rt)

    @rt("/api/launch")
    def launch_data(request: Request):
        global DATA_IS_LOADED
        if not DATA_IS_LOADED:
            init_load_data()
            DATA_IS_LOADED = True
        return {"data_is_loaded": DATA_IS_LOADED}

    @rt("/api/leader-select")
    def get_leader_select(request: Request):
        # Parse params using Pydantic model
        params = LeaderSelectParams(**get_query_params_as_dict(request))
        
        # Create and return the updated leader select
        return create_leader_select(params.meta_format, params.lid)

    @rt("/api/leaderboard")
    def api_leaderboard(request: Request):
        # Parse the sort and meta format parameters
        sort_params = LeaderboardSort(**get_query_params_as_dict(request))
        
        # Get filtered leaders
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
        if sort_params.sort_by == LeaderboardSortBy.TOURNAMENT_WINS:
            filtered_leaders.sort(key=lambda x: (x.tournament_wins > 0, x.tournament_wins, x.elo), reverse=True)
        else:
            filtered_leaders.sort(key=lambda x: getattr(x, display_name2df_col_name.get(sort_params.sort_by)), reverse=True)
        
        # Create the leaderboard table
        return create_leaderboard_table(
            filtered_leaders,
            sort_params.meta_format
        )

    @rt("/api/leader-data")
    async def get_leader_data(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
            
        # Get leader data
        if params.lid:
            # If a leader ID is provided, get data for that specific leader
            leader_data = get_leader_extended(leader_ids=[params.lid])
        else:
            # Otherwise, get all leaders and find the one with highest d_score
            leader_data = get_leader_extended()
            
        # Filter by meta format
        filtered_by_meta = [l for l in leader_data if l.meta_format in params.meta_format]
        
        # Apply filters
        filtered_data = filter_leader_extended(
            leaders=filtered_by_meta,
            only_official=params.only_official
        )
        
        if not filtered_data:
            return ft.P("No data available for this leader.", cls="text-red-400")
            
        # If no specific leader was requested, find the one with highest d_score
        if not params.lid:
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
            
            leader_data = next((l for l in filtered_data if l.id == params.lid), None)
            
            if not leader_data:
                return ft.P("No data available for this leader in the selected meta format.", cls="text-red-400")
        
        # Use the shared create_leader_content function
        return create_leader_content(leader_data)
