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
        value=default_id,
        cls="lp-select styled-select",
        *[ft.Option(
            name,
            value=lid,
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

    wr_style = "color:#10b981" if matchup.win_rate >= 0.5 else "color:#ef4444"

    return ft.A(
        ft.Div(
            # Image Area with zoomed background + gradient
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
                ft.P(opponent.name, style="font-family:'Barlow',sans-serif; font-size:0.7rem; font-weight:600; color:#f1f5f9; text-align:center; margin-bottom:4px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"),
                ft.Div(
                    ft.Span(f"{matchup.win_rate * 100:.1f}%", style=f"font-family:'Share Tech Mono',monospace; font-size:0.8rem; font-weight:700; {wr_style}"),
                    ft.Span(f" ({matchup.total_matches})", style="font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#475569; margin-left:4px;"),
                    style="display:flex; align-items:center; justify-content:center;"
                ),
                style="padding:6px 8px; background:#0d1424; border-radius:0 0 8px 8px;"
            ),
            style="display:flex; flex-direction:column; align-items:center; width:100%; height:100%; border-radius:8px; border:1px solid #1a2540; transition: border-color 0.15s, box-shadow 0.15s;"
        ),
        href=leader_url,
        cls="block flex-shrink-0",
        style="width:120px; min-width:120px; text-decoration:none;"
    )

def create_matchup_analysis(leader_data: LeaderExtended, matchups: OpponentMatchups | None = None, hx_include: str | None = None, min_matches: int = 4, matchup_cards: list[ft.A] | None = None):
    """Create the matchup analysis view with best and worst matchups."""
    
    # Slider Component
    slider_component = ft.Div(
        ft.H3("All Matchups", cls="lp-display", style="font-size:1.1rem; color:#f1f5f9; margin:0;"),
        ft.Div(
            ft.Label("Min Matches:", style="font-family:'Barlow',sans-serif; font-size:0.8rem; color:#94a3b8; margin-right:8px;"),
            ft.Span(str(min_matches), id="min-matches-display", style="font-family:'Share Tech Mono',monospace; color:#38bdf8; font-weight:700; margin-right:12px;"),
            ft.Input(
                type="range",
                min="1",
                max="50",
                value=str(min_matches),
                name="min_matches",
                id="min-matches-slider",
                cls="accent-cyan-400",
                style="width:120px; cursor:pointer; accent-color:#38bdf8;",
                oninput="document.getElementById('min-matches-display').innerText = this.value",
                hx_get="/api/leader-matchups",
                hx_target="#matchup-analysis-container",
                hx_swap="outerHTML",
                hx_trigger="change",
                hx_include=hx_include,
                hx_vals=f'{{"lid": "{leader_data.id}"}}'
            ),
            style="display:flex; align-items:center;"
        ),
        style="display:flex; flex-direction:column; gap:8px; margin-bottom:16px;"
    )

    if not matchups:
        return ft.Div(
            ft.H2("Matchup Analysis", cls="lp-display", style="font-size:1.4rem; color:#f1f5f9; margin-bottom:16px;"),
            ft.Div(
                slider_component,
                ft.P("No matchup data available for this leader with current filters.", style="color:#475569; font-family:'Barlow',sans-serif;"),
                style="width:100%; margin-bottom:24px;"
            ),
            id="matchup-analysis-container",
            cls="w-full"
        )

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
        ft.H2("Matchup Analysis", cls="lp-display", style="font-size:1.4rem; color:#f1f5f9; margin-bottom:16px;"),

        # Horizontal Matchup List Section
        ft.Div(
            slider_component,
            list_content,
            style="width:100%; margin-bottom:24px;"
        ),

        # Matchup grid
        ft.Div(
            # Best Matchup
            ft.Div(
                ft.H3("Easiest Matchup", cls="lp-display", style="font-size:1rem; color:#10b981; margin-bottom:12px;"),
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
                    cls="lp-panel", style="padding:16px; margin-top:12px;"
                ),
                style="width:100%;"
            ),

            # Radar Chart
            ft.Div(
                ft.H3("Color Matchups", cls="lp-display", style="font-size:1rem; color:#f1f5f9; margin-bottom:12px;"),
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
                style="width:100%;"
            ),

            # Worst Matchup
            ft.Div(
                ft.H3("Hardest Matchup", cls="lp-display", style="font-size:1rem; color:#ef4444; margin-bottom:12px;"),
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
                    cls="lp-panel", style="padding:16px; margin-top:12px;"
                ),
                style="width:100%;"
            ),
            cls="grid grid-cols-1 md:grid-cols-3 gap-6"
        ),
        id="matchup-analysis-container"
    )
