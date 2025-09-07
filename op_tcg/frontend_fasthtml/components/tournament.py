from fasthtml import ft
from datetime import datetime, date
from typing import Dict, List
from op_tcg.backend.models.tournaments import TournamentExtended, TournamentDecklist
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.matches import Match, MatchResult
from op_tcg.backend.models.input import MetaFormatRegion
from op_tcg.frontend_fasthtml.utils.charts import create_stream_chart
from op_tcg.frontend_fasthtml.utils.colors import ChartColors
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.backend.models.cards import Card

def create_leader_grid(leader_stats: Dict[str, float], leader_extended_dict: Dict[str, LeaderExtended], 
                      cid2cdata_dict: dict, max_leaders: int | None=None, 
                      selected_leader_id: str | None = None, tournament_id: str | None = None) -> ft.Div:
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
            is_selected = selected_leader_id == lid
            card_classes = "w-full transform transition-transform hover:scale-105 cursor-pointer"
            if is_selected:
                card_classes += " ring-2 ring-blue-400"
                
            leader_card = ft.Div(
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
                    # Selection indicator
                    ft.Div(
                        "✓",
                        cls="absolute top-2 right-2 bg-blue-500 text-white rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold"
                    ) if is_selected else None,
                    cls="relative w-full pb-[100%]"  # Square aspect ratio
                ),
                cls=card_classes,
                hx_get="/api/tournament-select-leader",
                hx_target="#tournament-leader-content",
                hx_trigger="click",
                hx_include="[name='meta_format'],[name='region']",
                hx_vals={"tournament_id": tournament_id, "selected_leader_id": lid} if tournament_id else None,
                hx_indicator="#tournament-leader-loading"
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
                             hx_include: str) -> ft.Div:
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

def create_match_progression(matches: List[Match], leader_extended_dict: Dict[str, LeaderExtended], 
                           cid2cdata_dict: dict, selected_leader_id: str) -> ft.Div:
    """Create a match progression timeline for a leader in a tournament."""
    if not matches:
        return ft.Div(
            ft.P("No detailed match data available for this tournament.", cls="text-gray-400 text-center py-8"),
            ft.P("Match data might not be recorded for this tournament", cls="text-gray-500 text-sm text-center"),
            cls="bg-gray-800 rounded-lg p-6"
        )
    
    # Group matches by round/phase
    rounds = {}
    for match in matches:
        round_key = f"Round {match.tournament_round}" if match.tournament_round else "Unknown Round"
        if match.tournament_phase:
            round_key += f" (Phase {match.tournament_phase})"
        
        if round_key not in rounds:
            rounds[round_key] = []
        rounds[round_key].append(match)
    
    # Create match progression timeline
    round_elements = []
    total_wins = 0
    total_losses = 0
    
    for round_name, round_matches in rounds.items():
        match_elements = []
        
        for match in round_matches:
            # Get opponent info
            opponent_id = match.opponent_id
            opponent_data = leader_extended_dict.get(opponent_id)
            opponent_card = cid2cdata_dict.get(opponent_id)
            opponent_name = opponent_card.name if opponent_card else opponent_id
            opponent_image = opponent_data.aa_image_url if opponent_data and opponent_data.aa_image_url else (opponent_data.image_url if opponent_data else None)
            
            # Determine result and styling
            if match.result == MatchResult.WIN:
                result_text = "Won"
                result_color = "text-green-400"
                bg_color = "bg-green-900/30 border-green-600"
                total_wins += 1
            elif match.result == MatchResult.LOSE:
                result_text = "Lost"
                result_color = "text-red-400"
                bg_color = "bg-red-900/30 border-red-600"
                total_losses += 1
            else:
                result_text = "Draw"
                result_color = "text-yellow-400"
                bg_color = "bg-yellow-900/30 border-yellow-600"
            
            # Create match card
            match_card = ft.Div(
                ft.Div(
                    # Opponent image
                    ft.Div(
                        ft.Img(
                            src=opponent_image,
                            cls="w-16 h-16 object-cover rounded-lg"
                        ) if opponent_image else ft.Div(
                            opponent_id[:8] + "...",
                            cls="w-16 h-16 bg-gray-600 rounded-lg flex items-center justify-center text-white text-xs"
                        ),
                        cls="flex-shrink-0"
                    ),
                    
                    # Match details
                    ft.Div(
                        ft.P(f"vs {opponent_name}", cls="font-semibold text-white"),
                        ft.P(f"Result: {result_text}", cls=f"text-sm {result_color}"),
                        ft.P(f"Table: {match.tournament_table}", cls="text-xs text-gray-400") if match.tournament_table else None,
                        ft.P(f"Match: {match.tournament_match}", cls="text-xs text-gray-400") if match.tournament_match else None,
                        cls="flex-1 ml-4"
                    ),
                    
                    cls="flex items-center"
                ),
                cls=f"border rounded-lg p-4 {bg_color}"
            )
            
            match_elements.append(match_card)
        
        # Create round section
        round_section = ft.Div(
            ft.H5(round_name, cls="text-lg font-bold text-white mb-3"),
            ft.Div(*match_elements, cls="space-y-3"),
            cls="mb-6"
        )
        round_elements.append(round_section)
    
    # Create summary
    summary = ft.Div(
        ft.H4("Match Summary", cls="text-xl font-bold text-white mb-4"),
        ft.Div(
            ft.Div(
                ft.Span("Wins: ", cls="text-gray-300"),
                ft.Span(str(total_wins), cls="text-green-400 font-bold"),
                cls="mr-6"
            ),
            ft.Div(
                ft.Span("Losses: ", cls="text-gray-300"),
                ft.Span(str(total_losses), cls="text-red-400 font-bold"),
                cls="mr-6"
            ),
            ft.Div(
                ft.Span("Win Rate: ", cls="text-gray-300"),
                ft.Span(f"{(total_wins / (total_wins + total_losses) * 100):.1f}%" if (total_wins + total_losses) > 0 else "N/A", 
                       cls="text-blue-400 font-bold"),
            ),
            cls="flex flex-wrap"
        ),
        cls="bg-gray-800 rounded-lg p-4 mb-6"
    )
    
    return ft.Div(
        summary,
        ft.H4("Match Progression", cls="text-xl font-bold text-white mb-4"),
        ft.Div(*round_elements, cls="space-y-4"),
        cls="space-y-6"
    ) 

def create_decklist_selector(leader_decklists: list, selected_decklist_index: int = 0, 
                           tournament_id: str = None, selected_leader_id: str = None) -> ft.Div:
    """Create a decklist selector when a leader has multiple decklists in a tournament."""
    
    if len(leader_decklists) <= 1:
        return None
    
    # Create options for each decklist
    options = []
    for i, decklist in enumerate(leader_decklists):
        placing_text = f"#{decklist.placing}" if decklist.placing is not None else "Unplaced"
        option_text = f"{placing_text} - {decklist.player_id if decklist.player_id else 'Unknown Player'}"
        
        options.append(
            ft.Option(
                option_text,
                value=str(i),
                selected=(i == selected_decklist_index),
                cls="text-white"
            )
        )
    
    select_id = f"decklist-selector-{tournament_id}-{selected_leader_id}"
    
    return ft.Div(
        ft.Label("Select Decklist:", cls="text-white font-medium block mb-2"),
        ft.Select(
            *options,
            id=select_id,
            name="selected_decklist_index",
            cls="styled-select w-full",
            hx_get="/api/tournament-select-leader",
            hx_target="#tournament-leader-content",
            hx_trigger="change",
            hx_include="[name='meta_format'],[name='region'],[name='tournament_id'],[name='selected_leader_id']",
            hx_vals={
                "tournament_id": tournament_id,
                "selected_leader_id": selected_leader_id
            } if tournament_id and selected_leader_id else None,
            hx_indicator="#tournament-leader-loading"
        ),
        # Script to initialize the select after it's rendered
        ft.Script(f"""
            setTimeout(() => {{
                if (window.initializeSelect) {{
                    console.log('Initializing decklist selector: {select_id}');
                    window.initializeSelect('{select_id}');
                }} else {{
                    console.error('initializeSelect function not available');
                }}
            }}, 100);
        """),
        cls="mb-4"
    )

 