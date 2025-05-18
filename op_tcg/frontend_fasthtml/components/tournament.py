from fasthtml import ft
from datetime import datetime, date
from typing import Dict, List
from op_tcg.backend.models.tournaments import TournamentExtended, TournamentDecklist
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormatRegion
from op_tcg.frontend_fasthtml.utils.charts import create_stream_chart
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.backend.models.cards import Card

def create_leader_grid(leader_stats: Dict[str, float], leader_extended_dict: Dict[str, LeaderExtended], 
                      cid2cdata_dict: dict, max_leaders: int | None=None) -> ft.Div:
    """Create a grid of leader images with participation percentages."""
    # Calculate total share of known leaders
    total_known_share = sum(leader_stats.values())
    
    # Add unknown leaders if there's remaining share
    if total_known_share < 1.0:
        unknown_share = 1.0 - total_known_share
        leader_stats['unknown'] = unknown_share
    
    # Sort leaders by participation
    sorted_leaders = sorted(leader_stats.items(), key=lambda x: x[1], reverse=True)
    if max_leaders is not None:
        sorted_leaders = sorted_leaders[:max_leaders]
    
    # Create rows of 4 leaders each
    rows = []
    current_row = []
    
    for lid, share in sorted_leaders:
        if lid == 'unknown':
            # Create card for unknown leaders
            cdata = cid2cdata_dict.get('default') or Card.from_default()
            leader_card = ft.Div(
                ft.Div(
                    ft.Img(
                        src=cdata.image_url,
                        cls="w-full h-full object-cover rounded-lg opacity-50"  # Added opacity for visual distinction
                    ),
                    # Overlay with percentage
                    ft.Div(
                        f"Unknown {share * 100:.1f}%",
                        cls="absolute bottom-0 right-0 bg-black bg-opacity-70 px-2 py-1 rounded-bl-lg rounded-tr-lg text-white text-sm"
                    ),
                    cls="relative w-full pb-[100%]"  # Square aspect ratio
                ),
                cls="w-full transform transition-transform hover:scale-105"
            )
        else:
            leader_data = leader_extended_dict.get(lid)
            if not leader_data:
                continue
                
            # Create leader card with image and percentage
            leader_card = ft.Div(
                ft.A(
                    ft.Div(
                        ft.Img(
                            src=leader_data.aa_image_url,
                            cls="w-full h-full object-cover rounded-lg"
                        ),
                        # Overlay with percentage
                        ft.Div(
                            f"{share * 100:.1f}%",
                            cls="absolute bottom-0 right-0 bg-black bg-opacity-70 px-2 py-1 rounded-bl-lg rounded-tr-lg text-white text-sm"
                        ),
                        cls="relative w-full pb-[100%]"  # Square aspect ratio
                    ),
                    href=f"/leader?lid={lid}",
                    cls="block w-full"
                ),
                cls="w-full transform transition-transform hover:scale-105"
            )
        
        current_row.append(leader_card)
        
        # Create a new row after every 4 leaders
        if len(current_row) == 4:
            rows.append(ft.Div(*current_row, cls="grid grid-cols-4 gap-4"))
            current_row = []
    
    # Add any remaining leaders in the last row
    if current_row:
        rows.append(ft.Div(*current_row, cls="grid grid-cols-4 gap-4"))
    
    return ft.Div(*rows, cls="space-y-4")

def create_tournament_section(leader_id: str, tournament_decklists: List[TournamentDecklist],
                            tournaments: List[TournamentExtended], leader_extended_dict: Dict[str, LeaderExtended],
                            cid2cdata_dict: dict, hx_include: str) -> ft.Div:
    """Create the tournament section for the leader page."""
    
    # Filter tournaments where this leader won
    tournaments_with_win = []
    day_count: Dict[date, int] = {}
    
    # Count tournament wins by date
    for td in tournament_decklists:
        if td.placing != 1:
            continue
        elif not isinstance(td.tournament_timestamp, datetime):
            continue
            
        t_date = td.tournament_timestamp.date()
        day_count[t_date] = day_count.get(t_date, 0) + 1
    
    # Get tournaments where this leader won
    for t in tournaments:
        if leader_id not in t.leader_ids_placings:
            continue
        elif 1 not in t.leader_ids_placings[leader_id]:
            continue
        tournaments_with_win.append(t)
    
    # Prepare chart data
    chart_data = [{"date": date.isoformat(), "wins": count} for date, count in sorted(day_count.items())]
    
    # Get leader color for the stream chart
    leader_color = leader_extended_dict[leader_id].to_hex_color() if leader_id in leader_extended_dict else ChartColors.POSITIVE
    
    # Get initial tournament for details
    initial_tournament = tournaments_with_win[0] if tournaments_with_win else None
    
    # Create the tournament section
    return ft.Div(
        # Tournament wins count and chart section
        ft.Div(
            ft.H3("Tournament Wins", cls="text-2xl font-bold text-white mb-4"),
            ft.P(f"Total Wins: {len(tournaments_with_win)}", cls="text-xl text-gray-200 mb-4"),
            
            # Tournament wins chart
            ft.Div(
                create_stream_chart(
                    container_id=f"tournament-wins-chart",
                    data=chart_data,
                    y_key="wins",
                    x_key="date",
                    y_label="Tournament Wins",
                    y_suffix=" wins",
                    color=leader_color,
                    show_x_axis=True,
                    show_y_axis=True
                ) if chart_data else ft.P("No tournament wins found", cls="text-gray-400"),
                cls="mb-8 h-[400px] bg-gray-800 rounded-lg p-0 md:p-6 shadow-lg"
            ),
            cls="mb-8"
        ),
        
        # Tournament details section
        ft.Div(
            ft.H4("Tournament Details", cls="text-xl font-bold text-white mb-4"),
            
            # Tournament selector
            ft.Select(
                *[ft.Option(t.name, value=t.id, selected=(t == initial_tournament)) for t in tournaments_with_win],
                name="tournament_id",
                cls="w-full p-2 bg-gray-700 text-white rounded-lg mb-4",
                hx_get="/api/tournament-details",
                hx_trigger="change, load",  # Added load trigger
                hx_target="#tournament-details",
                hx_include=f"{hx_include}[name='tournament_id']",
                hx_indicator="#tournament-details-loading"
            ) if tournaments_with_win else None,
            
            # Loading spinner
            create_loading_spinner(
                id="tournament-details-loading",
                size="w-8 h-8",
                container_classes="min-h-[50px]"
            ),
            
            # Tournament details container
            ft.Div(
                id="tournament-details",
                cls="space-y-4"
            ),
            
            cls="space-y-4 bg-gray-800 rounded-lg p-6 shadow-lg"
        ) if tournaments_with_win else None,
        
        cls="space-y-6"
    )

def create_tournament_keyfacts(tournament: TournamentExtended, winner_name: str) -> ft.Div:
    """Create a section displaying key facts about a tournament."""
    facts = [
        ("Name", tournament.name),
        ("Host", tournament.host) if tournament.host else None,
        ("Country", tournament.country) if tournament.country else None,
        ("Number Players", str(tournament.num_players) if tournament.num_players else "unknown"),
        ("Winner", winner_name),
        ("Date", tournament.tournament_timestamp.date() if isinstance(tournament.tournament_timestamp, datetime) else "unknown")
    ]
    
    # Filter out None values and create fact elements
    fact_elements = [
        ft.P(
            f"{label_and_value[0]}: {label_and_value[1]}",
            cls="text-gray-200"
        ) for label_and_value in facts if label_and_value is not None
    ]
    
    return ft.Div(
        *fact_elements,
        cls="space-y-2 mb-6"  # Added margin bottom
    ) 