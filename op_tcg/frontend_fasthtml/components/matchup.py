from fasthtml import ft
from enum import StrEnum    
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.api.models import Matchup, OpponentMatchups
from op_tcg.frontend_fasthtml.utils.leader_data import lid_to_name_and_lid

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

def create_matchup_analysis(leader_data: LeaderExtended, matchups: OpponentMatchups | None = None, hx_include: str | None = None):
    """Create the matchup analysis view with best and worst matchups."""
    
    if not matchups:
        return ft.P("No matchup data available for this leader.", cls="text-gray-400")
    
    # Get leader IDs for best and worst matchups
    best_matchup_ids = [m.leader_id for m in matchups.easiest_matchups]
    worst_matchup_ids = [m.leader_id for m in matchups.hardest_matchups]
    
    # Get default selections
    default_best = best_matchup_ids[0] if best_matchup_ids else None
    default_worst = worst_matchup_ids[0] if worst_matchup_ids else None
    
    return ft.Div(
        ft.H2("Matchup Analysis", cls="text-2xl font-bold text-white mb-4"),
        
        # Matchup grid
        ft.Div(
            # Best Matchup
            ft.Div(
                ft.H3("Best Matchup", cls="text-xl font-bold text-white mb-4"),
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
                ft.H3("Worst Matchup", cls="text-xl font-bold text-white mb-4"),
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
        cls="w-full"
    ) 