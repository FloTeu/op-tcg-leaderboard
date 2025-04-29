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
from op_tcg.frontend_fasthtml.utils.launch import init_load_data
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended
#from op_tcg.frontend_fasthtml.utils.leader_data import get_lid2ldata_dict_cached, lids_to_name_and_lids, lname_and_lid_to_lid, calculate_dominance_score

DATA_IS_LOADED = False

def setup_api_routes(rt):
    @rt("/api/launch")
    def launch_data(request: Request):
        global DATA_IS_LOADED
        if not DATA_IS_LOADED:
            init_load_data()
            DATA_IS_LOADED = True
        return {"data_is_loaded": DATA_IS_LOADED}

    @rt("/api/leaderboard")
    def api_leaderboard(request: Request):
        max_max_match_count = 10000
        # Get query parameters from request
        meta_format = MetaFormat(request.query_params.get("meta_format", MetaFormat.latest_meta_format))
        release_meta_formats = request.query_params.getlist("release_meta_formats")
        region = MetaFormatRegion(request.query_params.get("region", MetaFormatRegion.ALL))
        only_official = request.query_params.get("only_official", "true").lower() == "true"
        sort_by = LeaderboardSortBy(request.query_params.get("sort_by", LeaderboardSortBy.WIN_RATE))
        min_match_count = int(request.query_params.get("min_matches", 0))
        max_match_count = int(request.query_params.get("max_matches", max_max_match_count))
        
        # Get leader extended data
        leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=region)
        
        # Apply filters
        filtered_leaders = filter_leader_extended(
            leaders=leader_extended_data,
            only_official=only_official,
            release_meta_formats=release_meta_formats if release_meta_formats else None,
            match_count_min=min_match_count if min_match_count else None,
            match_count_max=max_match_count if max_match_count != max_max_match_count else None
        )
        
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
            meta_format,
            display_name2df_col_name,
            only_official
        )