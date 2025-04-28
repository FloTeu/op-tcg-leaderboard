from fasthtml import ft
from starlette.requests import Request
import pandas as pd
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.backend.models.cards import OPTcgColor
from op_tcg.backend.models.matches import Match, MatchResult
from op_tcg.backend.models.bq_enums import BQDataset
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table
#from op_tcg.frontend_fasthtml.utils.leader_data import get_lid2ldata_dict_cached, lids_to_name_and_lids, lname_and_lid_to_lid, calculate_dominance_score


def setup_api_routes(rt):
    @rt("/api/leaderboard")
    def api_leaderboard(request: Request):
        # Get query parameters from request
        meta_format = request.query_params.get("meta_format", MetaFormat.latest_meta_format)
        region = request.query_params.get("region", MetaFormatRegion.ALL)
        only_official = request.query_params.get("only_official", "true").lower() == "true"
        sort_by = request.query_params.get("sort_by", LeaderboardSortBy.WIN_RATE)
        
        leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=region)
        # Convert leader extended data to DataFrame
        df_leader_extended = pd.DataFrame([{
            "id": leader.id,
            "name": leader.name,
            "meta_format": leader.meta_format,
            "win_rate": leader.win_rate,
            "total_matches": leader.total_matches,
            "elo": leader.elo,
            "tournament_wins": leader.tournament_wins,
            "d_score": leader.d_score,
        } for leader in leader_extended_data])

        
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