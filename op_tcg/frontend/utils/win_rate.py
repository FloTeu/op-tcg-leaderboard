from op_tcg.backend.models.cards import ExtendedCardData, OPTcgColor
from op_tcg.backend.models.matches import LeaderWinRate
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.utils.extract import get_leader_win_rate, get_card_id_card_data_lookup
from typing import List, Dict, Any

def get_win_rate_data_by_leader(leader_id: str, meta_formats, only_official: bool = True) -> list[LeaderWinRate]:
    """
    Get win rate data for a specific leader against other leaders.
    
    Args:
        leader_id: The ID of the leader to get data for
        meta_formats: List of meta formats to include
        only_official: Whether to only include official matches
        
    Returns:
        List of win rate data for the leader
    """
    # Get all win rate data
    win_rate_data = get_leader_win_rate(meta_formats=meta_formats)
    
    # Filter by leader ID and official status
    filtered_data = [
        data for data in win_rate_data 
        if data.leader_id == leader_id 
        and data.only_official == only_official
        and data.meta_format in meta_formats
    ]
    
    return filtered_data

def get_color_win_rates(leader_ids: list[str], win_rate_data: list[LeaderWinRate], cid2cdata_dict: dict[str, ExtendedCardData]) -> List[Dict[str, Any]]:
    """
    Calculate win rates against different color identities.
    
    Args:
        leader_ids: List of leader IDs to process
        win_rate_data: Raw win rate data
        cid2cdata_dict: Dictionary mapping card IDs to card data
    
    Returns:
        List of dictionaries with win rates by color for each leader
    """
    # Initialize leader data structure
    leader_data = {}
    for leader_id in leader_ids:
        leader_data[leader_id] = {
            'leader_id': leader_id,
        }
        # Initialize all colors with zero
        for color_value in OPTcgColor.to_list():
            leader_data[leader_id][color_value] = 0
    
    # Initialize match counters
    color_matches = {}
    for leader_id in leader_ids:
        color_matches[leader_id] = {}
        for color_value in OPTcgColor.to_list():
            color_matches[leader_id][color_value] = {'matches': 0, 'wins': 0}
    
    # Process win rate data
    for data in win_rate_data:
        if data.leader_id in leader_ids:
            if data.opponent_id not in cid2cdata_dict:
                continue
                
            # Get opponent colors
            opponent_colors = cid2cdata_dict[data.opponent_id].colors
            
            # For each color the opponent has, count this matchup
            for color in opponent_colors:
                if color in OPTcgColor.to_list():
                    color_matches[data.leader_id][color]['matches'] += data.total_matches
                    color_matches[data.leader_id][color]['wins'] += int(data.total_matches * data.win_rate)
    
    # Calculate win rates
    for leader_id in leader_ids:
        for color_key in OPTcgColor.to_list():
            matches = color_matches[leader_id][color_key]['matches']
            if matches > 0:
                win_rate = color_matches[leader_id][color_key]['wins'] / matches
                leader_data[leader_id][color_key] = round(win_rate * 100, 1)
    
    # Return list of leader data
    return [leader_data[leader_id] for leader_id in leader_ids]


def get_radar_chart_data(leader_ids: list[str], meta_formats, only_official: bool = True):
    """
    Prepare radar chart data for the given leaders.
    
    Args:
        leader_ids: List of leader IDs to include in the chart
        meta_formats: List of meta formats to include
        only_official: Whether to only include official matches
        
    Returns:
        List of dictionaries with radar chart data in the format:
        [{'leader_id': 'leader1', 'RED': 60.5, 'BLUE': 55.2, ...}, ...]
    """
    # Get card data lookup
    cid2cdata_dict = get_card_id_card_data_lookup()
    
    # Get win rate data for the specified leaders
    all_win_rate_data = []
    for leader_id in leader_ids:
        leader_data = get_win_rate_data_by_leader(
            leader_id=leader_id, 
            meta_formats=meta_formats, 
            only_official=only_official
        )
        all_win_rate_data.extend(leader_data)
    
    # Get color win rates
    color_win_rates = get_color_win_rates(leader_ids, all_win_rate_data, cid2cdata_dict)
    
    # Convert to the format expected by create_leader_win_rate_radar_chart
    formatted_data = []
    for leader_data in color_win_rates:
        formatted_leader_data = {'leader_id': leader_data['leader_id']}
        for color in OPTcgColor.to_list():
            if color in leader_data:
                formatted_leader_data[color] = leader_data[color]
        formatted_data.append(formatted_leader_data)
    
    return formatted_data 