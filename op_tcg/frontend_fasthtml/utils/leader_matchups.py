from op_tcg.frontend_fasthtml.utils.extract import get_leader_win_rate
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend_fasthtml.api.models import Matchup, OpponentMatchups
import pandas as pd

def get_best_worst_matchups(leader_id: str, meta_formats: list[MetaFormat]) -> OpponentMatchups | None:
    """Get the best and worst matchups for a leader."""
    # Get win rate data
    win_rate_data: list[LeaderWinRate] = get_leader_win_rate(meta_formats=meta_formats)
    df = pd.DataFrame([wr.model_dump() for wr in win_rate_data])
    
    # Filter for the specific leader and meta formats
    df_filtered = df[
        (df['leader_id'] == leader_id) & 
        (df['meta_format'].isin(meta_formats))
    ]

    # min 10 or 10% of the max total matches
    max_total_matches = df_filtered['total_matches'].max()
    threshold = min(int(max_total_matches / 10), 10)
    df_filtered = df_filtered[df_filtered['total_matches'] > threshold]
    
    if df_filtered.empty:
        return None
        
    # Calculate win rate chart data for each opponent
    opponent_chart_data = {}
    for opponent_id in df_filtered['opponent_id'].unique():
        opponent_df = df_filtered[df_filtered['opponent_id'] == opponent_id]
        opponent_chart_data[opponent_id] = {
            meta: float(opponent_df[opponent_df['meta_format'] == meta]['win_rate'].mean())
            for meta in opponent_df['meta_format'].unique()
        }
    
    # Create matchups for best and worst opponents
    def create_matchup_list(df_group) -> list[Matchup]:
        return [
            Matchup(
                leader_id=opponent_id,
                win_rate=float(stats['win_rate'].mean()),
                total_matches=int(stats['total_matches'].sum()),
                meta_formats=list(stats['meta_format'].unique()),
                win_rate_chart_data=opponent_chart_data[opponent_id]
            )
            for opponent_id, stats in df_group
        ]
    
    # Get best matchups (highest win rate)
    best_matchups = create_matchup_list(df_filtered.groupby('opponent_id'))
    best_matchups.sort(key=lambda x: x.win_rate, reverse=True)
    
    # Get worst matchups (lowest win rate)
    worst_matchups = create_matchup_list(df_filtered.groupby('opponent_id'))
    worst_matchups.sort(key=lambda x: x.win_rate)
    
    return OpponentMatchups(
        easiest_matchups=best_matchups[:10],  # Top 10 best matchups
        hardest_matchups=worst_matchups[:10]  # Top 10 worst matchups
    ) 