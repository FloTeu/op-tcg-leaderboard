from fasthtml import ft
from datetime import datetime, date
from typing import Dict, List
from op_tcg.backend.models.tournaments import TournamentExtended, TournamentDecklist
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.input import MetaFormatRegion
from op_tcg.frontend_fasthtml.utils.charts import create_stream_chart, create_bar_chart
from op_tcg.frontend_fasthtml.utils.colors import ChartColors

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
        cls="space-y-2"
    )

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
                cls="mb-8 h-[400px] bg-gray-800 rounded-lg p-6 shadow-lg"
            ),
            cls="mb-8"
        ),
        
        # Tournament details section
        ft.Div(
            ft.H4("Tournament Details", cls="text-xl font-bold text-white mb-4"),
            
            # Tournament selector
            ft.Select(
                *[ft.Option(t.name, value=t.id) for t in tournaments_with_win],
                name="tournament_id",
                cls="w-full p-2 bg-gray-700 text-white rounded-lg mb-4",
                hx_get="/api/tournament-details",
                hx_trigger="change",
                hx_target="#tournament-details",
                hx_include=f"{hx_include}[name='tournament_id']"
            ) if tournaments_with_win else None,
            
            # Tournament details container
            ft.Div(
                id="tournament-details",
                cls="space-y-4"
            ),
            
            cls="space-y-4 bg-gray-800 rounded-lg p-6 shadow-lg"
        ) if tournaments_with_win else None,
        
        cls="space-y-6"
    ) 