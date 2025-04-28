from fasthtml import ft
from starlette.requests import Request
import pandas as pd
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderboardSortBy
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table

def setup_api_routes(rt):
    @rt("/api/leaderboard")
    def api_leaderboard(request: Request):
        # Get query parameters from request
        meta_format = request.query_params.get("meta_format", MetaFormat.latest_meta_format)
        region = request.query_params.get("region", MetaFormatRegion.ALL)
        only_official = request.query_params.get("only_official", "true").lower() == "true"
        sort_by = request.query_params.get("sort_by", LeaderboardSortBy.WIN_RATE)
        
        # TODO: Replace with actual data fetching logic
        # For now, using placeholder data
        df_leader_extended = pd.DataFrame({
            "id": ["OP01-001", "OP01-002"],
            "name": ["Monkey D. Luffy", "Roronoa Zoro"],
            "meta_format": [MetaFormat.OP01, MetaFormat.OP01],
            "win_rate": [0.65, 0.60],
            "total_matches": [100, 90],
            "elo": [1500, 1450],
            "tournament_wins": [5, 3],
            "d_score": [0.75, 0.70]
        })
        
        display_name2df_col_name = {
            "Name": "name",
            "Set": "id",
            LeaderboardSortBy.TOURNAMENT_WINS: "tournament_wins",
            "Match Count": "total_matches",
            LeaderboardSortBy.WIN_RATE: "win_rate",
            LeaderboardSortBy.DOMINANCE_SCORE: "d_score",
            "Elo": "elo"
        }
        
        # Create the leaderboard table
        return create_leaderboard_table(
            df_leader_extended,
            meta_format,
            display_name2df_col_name,
            only_official
        )