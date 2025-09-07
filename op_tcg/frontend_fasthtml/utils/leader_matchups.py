from op_tcg.frontend_fasthtml.utils.extract import get_leader_win_rate
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.api.models import Matchup, OpponentMatchups
from typing import Dict, List, Set

def get_opponent_win_rate_chart(leader_id: str, opponent_id: str, meta_formats: list[MetaFormat], only_official: bool = True) -> tuple[dict[str, float], dict[str, int]]:
    """Get the win rate chart data for opponents of a specific leader."""
    win_rate_chart_data = {}
    total_matches = {}
    win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=meta_formats)
    
    for wr in win_rate_data:
        if wr.leader_id == leader_id and wr.opponent_id == opponent_id and wr.only_official == only_official:
            win_rate_chart_data[wr.meta_format] = wr.win_rate
            total_matches[wr.meta_format] = wr.total_matches

    return win_rate_chart_data, total_matches

def calculate_average_win_rate(data: List[LeaderWinRate], opponent_id: str) -> float:
    """Calculate average win rate for a specific opponent."""
    opponent_matches = [wr for wr in data if wr.opponent_id == opponent_id]
    if not opponent_matches:
        return 0.0
    return sum(wr.win_rate for wr in opponent_matches) / len(opponent_matches)

def get_best_worst_matchups(leader_id: str, meta_formats: list[MetaFormat]) -> OpponentMatchups | None:
    """Get the best and worst matchups for a leader."""
    # Get win rate data
    win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=meta_formats)
    
    # Filter for the specific leader and meta formats
    filtered_data = [
        wr for wr in win_rate_data 
        if wr.leader_id == leader_id and wr.meta_format in meta_formats
    ]
    
    if not filtered_data:
        return None

    # Calculate max total matches and threshold
    max_total_matches = max((wr.total_matches for wr in filtered_data), default=0)
    threshold = min(int(max_total_matches / 10), 10)
    
    # Filter by threshold
    filtered_data = [wr for wr in filtered_data if wr.total_matches > threshold]
    
    if not filtered_data:
        return None

    # Get unique opponent IDs
    opponent_ids = {wr.opponent_id for wr in filtered_data}
    
    # Calculate win rate chart data for each opponent
    opponent_chart_data: Dict[str, Dict[MetaFormat, float]] = {}
    for opponent_id in opponent_ids:
        opponent_matches = [wr for wr in filtered_data if wr.opponent_id == opponent_id]
        meta_formats_data = {}
        for meta in {wr.meta_format for wr in opponent_matches}:
            meta_matches = [wr for wr in opponent_matches if wr.meta_format == meta]
            if meta_matches:
                meta_formats_data[meta] = sum(wr.win_rate for wr in meta_matches) / len(meta_matches)
        opponent_chart_data[opponent_id] = meta_formats_data

    def create_matchup(opponent_id: str) -> Matchup:
        opponent_matches = [wr for wr in filtered_data if wr.opponent_id == opponent_id]
        return Matchup(
            leader_id=opponent_id,
            win_rate=sum(wr.win_rate for wr in opponent_matches) / len(opponent_matches),
            total_matches=sum(wr.total_matches for wr in opponent_matches),
            meta_formats=list({wr.meta_format for wr in opponent_matches}),
            win_rate_chart_data=opponent_chart_data[opponent_id]
        )

    # Create all matchups
    all_matchups = [create_matchup(opponent_id) for opponent_id in opponent_ids]
    
    # Sort matchups by win rate
    all_matchups.sort(key=lambda x: x.win_rate)
    
    return OpponentMatchups(
        easiest_matchups=sorted(all_matchups, key=lambda x: x.win_rate, reverse=True)[:10],
        hardest_matchups=all_matchups[:10]
    ) 