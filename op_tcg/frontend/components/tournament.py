from fasthtml import ft
from datetime import datetime, date
from typing import Dict, List
from op_tcg.backend.models.tournaments import TournamentExtended, TournamentDecklist
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.matches import Match, MatchResult
from op_tcg.backend.models.input import MetaFormatRegion
from op_tcg.frontend.utils.charts import create_stream_chart
from op_tcg.frontend.utils.colors import ChartColors
from op_tcg.frontend.components.loading import create_loading_spinner
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
                card_classes += " ring-2 ring-amber-400"
                
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
                        cls="absolute top-2 right-2 rounded-full w-6 h-6 flex items-center justify-center text-sm font-bold",
                        style="background:#f59e0b; color:#000;"
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
            ft.Div(
                ft.H3("Tournament Wins", cls="lp-display", style="font-size:1.2rem; color:#f1f5f9; margin:0;"),
                ft.Span(
                    str(len(tournaments_with_win)),
                    style="font-family:'Share Tech Mono',monospace; font-size:1.4rem; color:#f59e0b; font-weight:700;"
                ),
                style="display:flex; align-items:baseline; gap:12px; margin-bottom:16px;"
            ),
            ft.Div(
                create_stream_chart(
                    container_id="tournament-wins-chart",
                    data=chart_data,
                    y_key="wins",
                    x_key="date",
                    y_label="Tournament Wins",
                    y_suffix=" wins",
                    color=leader_color,
                    show_x_axis=True,
                    show_y_axis=True
                ) if chart_data else ft.P("No tournament wins found", style="color:#475569; font-family:'Barlow',sans-serif;"),
                cls="lp-panel mb-8 h-[400px]", style="padding:0; overflow:hidden;"
            ),
            style="margin-bottom:24px;"
        ),

        # Tournament details section
        ft.Div(
            ft.H4("Tournament Details", cls="lp-display", style="font-size:1.1rem; color:#f1f5f9; margin-bottom:14px;"),
            ft.Select(
                *[ft.Option(t.name, value=t.id, selected=(t == initial_tournament)) for t in tournaments_with_win],
                name="tournament_id",
                cls="lp-select styled-select",
                style="margin-bottom:14px;",
                hx_get="/api/tournament-details",
                hx_trigger="change, load",
                hx_target="#tournament-details",
                hx_include=f"{hx_include}[name='tournament_id']",
                hx_indicator="#tournament-details-loading"
            ) if tournaments_with_win else None,
            create_loading_spinner(id="tournament-details-loading", size="w-8 h-8", container_classes="min-h-[50px]"),
            ft.Div(id="tournament-details", cls="space-y-4"),
            cls="lp-panel", style="padding:20px;"
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
        ft.Div(
            ft.Span(f"{label_and_value[0]}", style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.65rem; color:#334155; text-transform:uppercase;"),
            ft.Span(f" {label_and_value[1]}", style="font-family:'Barlow',sans-serif; font-size:0.85rem; color:#94a3b8;"),
            style="display:flex; align-items:baseline; gap:6px;"
        ) for label_and_value in facts if label_and_value is not None
    ]

    return ft.Div(
        *fact_elements,
        style="display:flex; flex-direction:column; gap:6px; margin-bottom:20px;"
    ) 

def create_match_progression(matches: List[Match], leader_extended_dict: Dict[str, LeaderExtended], 
                           cid2cdata_dict: dict, selected_leader_id: str) -> ft.Div:
    """Create a match progression timeline for a leader in a tournament."""
    if not matches:
        return ft.Div(
            ft.P("No detailed match data available for this tournament.", style="color:#475569; font-family:'Barlow',sans-serif; text-align:center; padding:24px 0 8px;"),
            ft.P("Match data might not be recorded for this tournament", style="color:#334155; font-family:'Barlow',sans-serif; font-size:0.8rem; text-align:center;"),
            cls="lp-panel", style="padding:20px;"
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
                result_style = "color:#10b981"
                border_color = "rgba(16,185,129,0.35)"
                bg = "rgba(16,185,129,0.06)"
                total_wins += 1
            elif match.result == MatchResult.LOSE:
                result_text = "Lost"
                result_style = "color:#ef4444"
                border_color = "rgba(239,68,68,0.35)"
                bg = "rgba(239,68,68,0.06)"
                total_losses += 1
            else:
                result_text = "Draw"
                result_style = "color:#f59e0b"
                border_color = "rgba(245,158,11,0.35)"
                bg = "rgba(245,158,11,0.06)"

            # Create match card
            match_card = ft.Div(
                ft.Div(
                    ft.Div(
                        ft.Img(src=opponent_image, style="width:56px; height:56px; object-fit:cover; border-radius:6px;")
                        if opponent_image else ft.Div(
                            opponent_id[:8] + "...",
                            style="width:56px; height:56px; background:#080e1c; border:1px solid #1a2540; border-radius:6px; display:flex; align-items:center; justify-content:center; font-family:'Share Tech Mono',monospace; font-size:0.6rem; color:#475569;"
                        ),
                        style="flex-shrink:0;"
                    ),
                    ft.Div(
                        ft.P(f"vs {opponent_name}", style="font-family:'Barlow',sans-serif; font-weight:600; color:#f1f5f9; font-size:0.85rem; margin-bottom:2px;"),
                        ft.P(f"Result: {result_text}", style=f"font-family:'Bebas Neue',sans-serif; letter-spacing:0.08em; font-size:0.85rem; {result_style}"),
                        ft.P(f"Table: {match.tournament_table}", style="font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#475569;") if match.tournament_table else None,
                        ft.P(f"Match: {match.tournament_match}", style="font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#475569;") if match.tournament_match else None,
                        style="flex:1; margin-left:14px;"
                    ),
                    style="display:flex; align-items:center;"
                ),
                style=f"border-radius:8px; padding:12px; background:{bg}; border:1px solid {border_color};"
            )
            
            match_elements.append(match_card)
        
        # Create round section
        round_section = ft.Div(
            ft.H5(round_name, style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.85rem; color:#334155; text-transform:uppercase; margin-bottom:10px;"),
            ft.Div(*match_elements, style="display:flex; flex-direction:column; gap:8px;"),
            style="margin-bottom:20px;"
        )
        round_elements.append(round_section)
    
    win_rate_str = f"{(total_wins / (total_wins + total_losses) * 100):.1f}%" if (total_wins + total_losses) > 0 else "N/A"
    summary = ft.Div(
        ft.H4("Match Summary", style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9; margin-bottom:12px;"),
        ft.Div(
            ft.Div(
                ft.Span("Wins ", style="font-family:'Barlow',sans-serif; font-size:0.75rem; color:#475569; text-transform:uppercase; letter-spacing:0.05em;"),
                ft.Span(str(total_wins), style="font-family:'Share Tech Mono',monospace; color:#10b981; font-weight:700; font-size:1rem;"),
                style="display:flex; flex-direction:column; align-items:center; padding:8px 16px; background:rgba(16,185,129,0.06); border:1px solid rgba(16,185,129,0.2); border-radius:6px;"
            ),
            ft.Div(
                ft.Span("Losses ", style="font-family:'Barlow',sans-serif; font-size:0.75rem; color:#475569; text-transform:uppercase; letter-spacing:0.05em;"),
                ft.Span(str(total_losses), style="font-family:'Share Tech Mono',monospace; color:#ef4444; font-weight:700; font-size:1rem;"),
                style="display:flex; flex-direction:column; align-items:center; padding:8px 16px; background:rgba(239,68,68,0.06); border:1px solid rgba(239,68,68,0.2); border-radius:6px;"
            ),
            ft.Div(
                ft.Span("Win Rate", style="font-family:'Barlow',sans-serif; font-size:0.75rem; color:#475569; text-transform:uppercase; letter-spacing:0.05em;"),
                ft.Span(win_rate_str, style="font-family:'Share Tech Mono',monospace; color:#38bdf8; font-weight:700; font-size:1rem;"),
                style="display:flex; flex-direction:column; align-items:center; padding:8px 16px; background:rgba(56,189,248,0.06); border:1px solid rgba(56,189,248,0.2); border-radius:6px;"
            ),
            style="display:flex; gap:10px; flex-wrap:wrap;"
        ),
        cls="lp-panel", style="padding:16px; margin-bottom:20px;"
    )

    return ft.Div(
        summary,
        ft.H4("Match Progression", style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9; margin-bottom:16px;"),
        ft.Div(*round_elements),
        style="display:flex; flex-direction:column; gap:8px;"
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

 