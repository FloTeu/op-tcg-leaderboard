from fasthtml import ft
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.frontend_fasthtml.utils.charts import create_line_chart
from op_tcg.frontend_fasthtml.utils.extract import get_leader_extended
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended

def get_leader_win_rate_data(leader_data: LeaderExtended) -> list[dict]:
    """Create win rate history data for the chart."""
    # Get all meta formats up to the current one
    all_meta_formats = MetaFormat.to_list()
    current_meta_index = all_meta_formats.index(leader_data.meta_format)
    relevant_meta_formats = all_meta_formats[max(0, current_meta_index - 4):current_meta_index + 1]
    
    # Get leader data for all relevant meta formats
    all_leader_data = get_leader_extended(meta_formats=relevant_meta_formats)
    leader_history = [l for l in all_leader_data if l.id == leader_data.id]
    
    # Create a lookup for existing data points
    meta_to_leader = {l.meta_format: l for l in leader_history}
    
    # Prepare data for the chart, including null values for missing meta formats
    chart_data = []
    for meta_format in relevant_meta_formats:
        if meta_format in meta_to_leader:
            leader = meta_to_leader[meta_format]
            chart_data.append({
                "meta": str(meta_format),
                "winRate": round(leader.win_rate * 100, 2) if leader.win_rate is not None else None
            })
        else:
            chart_data.append({
                "meta": str(meta_format),
                "winRate": None
            })
    
    return chart_data

def leader_page(leader_id: str):
    """
    Display detailed information about a specific leader.
    """
    # Get leader data
    leader_data = None
    leader_extended_data = get_leader_extended(leader_ids=[leader_id])
    
    if leader_extended_data:
        # Filter for official matches
        filtered_data = filter_leader_extended(leader_extended_data, only_official=True)
        if filtered_data:
            leader_data = filtered_data[0]
    
    if not leader_data:
        return ft.Div(
            ft.P("No data available for this leader.", cls="text-red-400"),
            cls="min-h-screen p-8"
        )
    
    return ft.Div(
        # Header section with leader info
        ft.Div(
            ft.Div(
                # Left column - Leader image and basic stats
                ft.Div(
                    ft.Img(src=leader_data.aa_image_url, cls="w-full rounded-lg shadow-lg"),
                    ft.Div(
                        ft.H2(leader_data.name, cls="text-2xl font-bold text-white mt-4"),
                        ft.P(f"Set: {leader_data.id}", cls="text-gray-400"),
                        ft.Div(
                            ft.P(f"Win Rate: {leader_data.win_rate * 100:.1f}%" if leader_data.win_rate is not None else "Win Rate: N/A", 
                                 cls="text-green-400"),
                            ft.P(f"Total Matches: {leader_data.total_matches}" if leader_data.total_matches is not None else "Total Matches: N/A", 
                                 cls="text-blue-400"),
                            ft.P(f"Tournament Wins: {leader_data.tournament_wins}", cls="text-purple-400"),
                            ft.P(f"ELO Rating: {leader_data.elo}" if leader_data.elo is not None else "ELO Rating: N/A", 
                                 cls="text-yellow-400"),
                            cls="space-y-2 mt-4"
                        ),
                        cls="mt-4"
                    ),
                    cls="w-1/3"
                ),
                # Right column - Win rate chart
                ft.Div(
                    ft.H3("Win Rate History", cls="text-xl font-bold text-white mb-4"),
                    create_line_chart(
                        container_id=f"win-rate-chart-{leader_id}",
                        data=get_leader_win_rate_data(leader_data),
                        show_x_axis=True,
                        show_y_axis=True
                    ),
                    cls="w-2/3 pl-8"
                ),
                cls="flex gap-8"
            ),
            cls="bg-gray-800 rounded-lg p-6 shadow-xl"
        ),
        
        # Tabs section
        ft.Div(
            ft.Div(
                ft.H3("Recent Tournaments", cls="text-xl font-bold text-white"),
                ft.P("Coming soon...", cls="text-gray-400 mt-2"),
                cls="bg-gray-800 rounded-lg p-6 mt-6"
            ),
            ft.Div(
                ft.H3("Popular Decklists", cls="text-xl font-bold text-white"),
                ft.P("Coming soon...", cls="text-gray-400 mt-2"),
                cls="bg-gray-800 rounded-lg p-6 mt-6"
            ),
            ft.Div(
                ft.H3("Matchup Analysis", cls="text-xl font-bold text-white"),
                ft.P("Coming soon...", cls="text-gray-400 mt-2"),
                cls="bg-gray-800 rounded-lg p-6 mt-6"
            ),
            cls="space-y-6"
        ),
        cls="min-h-screen p-8"
    ) 