from fasthtml import ft
from enum import StrEnum    
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.api.models import Matchup, OpponentMatchups
from op_tcg.frontend.utils.leader_data import lid_to_name_and_lid
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion

class MatchupType(StrEnum):
    BEST = "best"
    WORST = "worst"

def create_leader_select_box(leader_ids: list[str], default_id: str | None = None, key: MatchupType = "", reverse: bool = False) -> ft.Div:
    """Create a styled leader select box."""
    # Sort leader IDs by name
    leader_names = [lid_to_name_and_lid(lid) for lid in leader_ids]
    if reverse:
        leader_names.reverse()
        leader_ids.reverse()
    
    return ft.Select(
        id=f"leader-select-{key}",
        name=f"lid_{key}",
        value=default_id,  # Set initial value
        cls="w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 styled-select",
        *[ft.Option(
            name, 
            value=lid,  # Use leader ID directly as value
            selected=(lid == default_id)
        ) for name, lid in zip(leader_names, leader_ids)]
    )

def create_matchup_card(opponent: LeaderExtended, matchup: Matchup, meta_formats: list[MetaFormat], region: MetaFormatRegion | None = None) -> ft.A:
    """Create a matchup card component."""
    # Determine color for win rate
    wr_color = "text-green-400" if matchup.win_rate >= 0.5 else "text-red-400"

    # Construct URL for leader page
    meta_format_params = "".join([f"&meta_format={mf}" for mf in meta_formats])
    region_param = f"&region={region}" if region else ""
    leader_url = f"/leader?lid={opponent.id}{meta_format_params}{region_param}"

    return ft.A(
        ft.Div(
            # Image Area with zoomed background
            ft.Div(
                style=f"""
                    background-image: linear-gradient(to top, {opponent.to_hex_color()}, transparent), url('{opponent.aa_image_url}');
                    background-size: cover, 125%;
                    background-position: center 20%;
                    height: 100px;
                    width: 100%;
                """,
                cls="rounded-t-lg w-full"
            ),
            # Content Area
            ft.Div(
                # Name
                ft.P(opponent.name, cls="text-xs text-white truncate w-full text-center font-bold mb-1"),
                # Stats
                ft.Div(
                    ft.Span(f"{matchup.win_rate * 100:.1f}%", cls=f"text-sm font-bold {wr_color}"),
                    ft.Span(f" ({matchup.total_matches})", cls="text-xs text-gray-400 ml-1"),
                    cls="flex items-center justify-center"
                ),
                cls="p-2 bg-gray-800 rounded-b-lg w-full"
            ),
            cls="flex flex-col items-center w-full h-full rounded-lg border border-gray-700 hover:border-gray-500 transition-colors duration-200 shadow-lg"
        ),
        href=leader_url,
        cls="block flex-shrink-0",
        style="width: 120px; min-width: 120px;"
    )

def create_matchup_analysis(leader_data: LeaderExtended, matchups: OpponentMatchups | None = None, hx_include: str | None = None, min_matches: int = 4, matchup_cards: list[ft.A] | None = None):
    """Create the matchup analysis view with best and worst matchups."""
    
    if not matchups:
        return ft.P("No matchup data available for this leader.", cls="text-gray-400")
    
    # Get leader IDs for best and worst matchups
    best_matchup_ids = [m.leader_id for m in matchups.easiest_matchups]
    worst_matchup_ids = [m.leader_id for m in matchups.hardest_matchups]
    
    # Get default selections
    default_best = best_matchup_ids[0] if best_matchup_ids else None
    default_worst = worst_matchup_ids[0] if worst_matchup_ids else None
    
    # Create list container content
    if matchup_cards:
        list_content = ft.Div(
            *matchup_cards,
            cls="flex flex-row gap-4 overflow-x-auto pb-4 scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800"
        )
    else:
        list_content = ft.Div(
            create_loading_spinner(
                id="matchup-list-loading",
                size="w-8 h-8",
                container_classes="min-h-[100px]"
            ),
            id="matchup-list-container",
            hx_get="/api/leader-matchups-list",
            hx_trigger="load",
            hx_include=f"{hx_include},[name='min_matches']",
            hx_vals=f'{{"lid": "{leader_data.id}"}}',
            hx_indicator="#matchup-list-loading",
            cls="w-full min-h-[150px]"
        )

    return ft.Div(
        ft.H2("Matchup Analysis", cls="text-2xl font-bold text-white mb-4"),
        
        # Horizontal Matchup List Section
        ft.Div(
            ft.Div(
                ft.H3("All Matchups", cls="text-xl font-bold text-white"),
                # Slider
                ft.Div(
                    ft.Label("Min Matches: ", cls="text-gray-300 mr-2"),
                    ft.Span(str(min_matches), id="min-matches-display", cls="text-white font-bold mr-4"),
                    ft.Input(
                        type="range",
                        min="1",
                        max="50",
                        value=str(min_matches),
                        name="min_matches",
                        id="min-matches-slider",
                        cls="w-48 h-2 bg-gray-700 rounded-lg appearance-none cursor-pointer accent-blue-500",
                        oninput="document.getElementById('min-matches-display').innerText = this.value",
                        hx_get="/api/leader-matchups",
                        hx_target="#matchup-analysis-container",
                        hx_swap="outerHTML",
                        hx_trigger="change",
                        hx_include=hx_include,
                        hx_vals=f'{{"lid": "{leader_data.id}"}}'
                    ),
                    cls="flex items-center"
                ),
                cls="flex justify-between items-center mb-4"
            ),

            # Container for the list
            list_content,
            cls="w-full mb-8"
        ),

        # Matchup grid
        ft.Div(
            # Best Matchup
            ft.Div(
                ft.H3("Easiest Matchup", cls="text-xl font-bold text-white mb-4"),
                create_leader_select_box(best_matchup_ids, default_best, MatchupType.BEST, reverse=False),
                ft.Div(
                    ft.Div(
                        id="best-matchup-content",
                        hx_get="/api/leader-matchup-details",
                        hx_trigger="load, change from:#leader-select-best",
                        hx_target="#best-matchup-content",
                        hx_include=hx_include + ",[name='lid_best']",
                        cls="w-full"
                    ),
                    cls="bg-gray-700 p-4 rounded-lg mt-4"
                ),
                cls="w-full"
            ),
            
            # Radar Chart
            ft.Div(
                ft.H3("Color Matchups", cls="text-xl font-bold text-white mb-4"),
                create_loading_spinner(
                    id="matchup-radar-loading",
                    size="w-8 h-8",
                    container_classes="min-h-[100px]"
                ),
                ft.Div(
                    hx_get="/api/leader-radar-chart",
                    hx_trigger="load, change from:#leader-select-best, change from:#leader-select-worst",
                    hx_include=f"{hx_include},[name='lid_best'],[name='lid_worst']",
                    hx_target="#matchup-radar-chart",
                    hx_indicator="#matchup-radar-loading",
                    hx_vals=f'{{"lid": "{leader_data.id}"}}',
                    id="matchup-radar-chart",
                    cls="min-h-[300px] flex items-center justify-center w-full"
                ),
                cls="w-full"
            ),
            
            # Worst Matchup
            ft.Div(
                ft.H3("Hardest Matchup", cls="text-xl font-bold text-white mb-4"),
                create_leader_select_box(worst_matchup_ids, default_worst, MatchupType.WORST, reverse=False),
                ft.Div(
                    ft.Div(
                        id="worst-matchup-content",
                        hx_get="/api/leader-matchup-details",
                        hx_trigger="load, change from:#leader-select-worst",
                        hx_target="#worst-matchup-content",
                        hx_include=hx_include + ",[name='lid_worst']",
                        cls="w-full"
                    ),
                    cls="bg-gray-700 p-4 rounded-lg mt-4"
                ),
                cls="w-full"
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-6"
        ),
        id="matchup-analysis-container"
    )
