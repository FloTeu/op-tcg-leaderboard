from collections import defaultdict
from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend_fasthtml.utils.extract import get_tournament_decklist_data, get_all_tournament_extened_data, get_tournament_match_data
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict, get_effective_meta_format_with_fallback, create_fallback_notification
from op_tcg.frontend_fasthtml.utils.extract import (
    get_leader_extended,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.tournament import (
    create_tournament_section,
    create_tournament_keyfacts,
    create_leader_grid,
    create_match_progression,
    create_decklist_selector
)
from op_tcg.frontend_fasthtml.components.tournament_decklist import create_decklist_view
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams, TournamentPageParams
from op_tcg.frontend_fasthtml.pages.leader import HX_INCLUDE
from op_tcg.frontend_fasthtml.utils.charts import create_bubble_chart, create_donut_chart
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
import json
from datetime import datetime, timedelta, timezone

def aggregate_leader_data(leader_data: list[LeaderExtended]):
    """Aggregate leader data by leader_id and calculate relative mean win rate."""
    aggregated_data = defaultdict(lambda: {
        "total_matches": [],
        "total_wins": [],
        "win_rate": [],
        "image_url": ""
    })
    
    for ld in leader_data:
        if ld.total_matches is not None:
            aggregated_data[ld.id]["total_matches"].append(ld.total_matches)
        if ld.tournament_wins is not None:
            aggregated_data[ld.id]["total_wins"].append(ld.tournament_wins)
        if ld.win_rate is not None:
            aggregated_data[ld.id]["win_rate"].append(ld.win_rate)
        aggregated_data[ld.id]["image_url"] = ld.aa_image_url if ld.aa_image_url else ld.image_url

    # Calculate relative mean win rate and prepare final data for chart
    final_leader_data = []
    for leader_id, data in aggregated_data.items():
        
        if len(data["total_matches"]) > 0:
            # for each list element get a relative factor by dividing the element by the sum of the list
            relative_factors = [x / sum(data["total_matches"]) for x in data["total_matches"]]
            # multiply the win rate list by the relative factors
            win_rates = [x * y for x, y in zip(data["win_rate"], relative_factors)]
            # calculate the mean of the win rates
            relative_mean_win_rate = sum(win_rates)
            final_leader_data.append({
                "leader_id": leader_id,
                "total_matches": sum(data["total_matches"]),
                "total_wins": sum(data["total_wins"]),
                "relative_mean_win_rate": relative_mean_win_rate,
                "image_url": data["image_url"]
            })
    
    return final_leader_data


def setup_api_routes(rt):

    @rt("/api/tournaments/max-matches")
    def get_max_matches(request: Request):
        """Return the maximum match count for setting slider bounds."""
        # Parse params using Pydantic model
        params = TournamentPageParams(**get_query_params_as_dict(request))
        
        # Get leader data
        leader_data = get_leader_extended(meta_format_region=params.region)
        
        # Filter by meta formats
        leader_data = [ld for ld in leader_data if ld.meta_format in params.meta_format and ld.only_official]

        # Calculate relative mean win rate and prepare final data for chart
        final_leader_data = aggregate_leader_data(leader_data)
        
        # Get maximum match count
        max_matches = max((ld.get("total_matches", 0) for ld in final_leader_data), default=1000)
        
        return {"max_matches": max_matches}

    @rt("/api/tournaments/chart")
    def get_tournament_chart(request: Request):
        """Return the tournament statistics chart."""
        # Parse params using Pydantic model
        params = TournamentPageParams(**get_query_params_as_dict(request))
        
        # Get leader data
        leader_data = get_leader_extended(meta_format_region=params.region)
        card_data = get_card_id_card_data_lookup()
        
        # Filter by meta formats first
        filtered_data = [ld for ld in leader_data if ld.meta_format in params.meta_format and ld.only_official]
        
        # Check if fallback is needed for any of the selected meta formats
        fallback_used = False
        effective_meta_formats = []
        
        for meta_format in params.meta_format:
            effective_meta, is_fallback = get_effective_meta_format_with_fallback(
                meta_format,
                filtered_data
            )
            effective_meta_formats.append(effective_meta)
            if is_fallback:
                fallback_used = True
        
        # If fallback was used, re-filter data to use effective meta formats
        if fallback_used:
            filtered_data = [ld for ld in leader_data if ld.meta_format in effective_meta_formats and ld.only_official]

        # Calculate relative mean win rate and prepare final data for chart
        final_leader_data = aggregate_leader_data(filtered_data)
        
        # Get max matches for slider bounds and set default if not provided
        max_matches = max((ld.get("total_matches", 0) for ld in final_leader_data), default=1000)
        if params.max_matches is None:
            effective_max_matches = max_matches
        else:
            effective_max_matches = params.max_matches
        
        # Filter by match count range
        final_leader_data = [ld for ld in final_leader_data if params.min_matches <= ld.get("total_matches", 0) <= effective_max_matches]
        
        # Process data for bubble chart - optimize for mobile by limiting data points
        chart_data = []
        colors = []
        
        # Sort by total matches descending to get most active leaders first
        sorted_leader_data = sorted(final_leader_data, key=lambda x: x.get("total_matches", 0), reverse=True)
        
        # Limit data points for better mobile experience - show top 25 most active leaders
        mobile_optimized_data = sorted_leader_data[:25]
        
        # First pass to get max values for scaling
        max_tournament_wins = max((ld.get("total_wins", 0) for ld in mobile_optimized_data), default=1)
        
        # Calculate bubble size scaling factor - smaller sizes for mobile
        base_size = 8   # Increased minimum bubble size for better visibility
        max_size = 25   # Reduced max size to prevent overcrowding
        
        for ld in mobile_optimized_data:
            if ld.get("total_matches", 0) is None:
                continue
            if ld.get("total_matches", 0) > 0:  # Only include leaders with matches
                card = card_data.get(ld.get("leader_id"))
                
                # Create color data for multi-color support (same as donut chart)
                if card and card.colors:
                    # For multi-color leaders, pass array of hex colors
                    leader_colors = [color.to_hex_color() for color in card.colors]
                else:
                    # Single color fallback
                    leader_colors = ["#808080"]
                
                # Scale bubble size based on tournament wins relative to max
                relative_size = (ld.get("total_wins") / max_tournament_wins) if max_tournament_wins > 0 else 0
                bubble_size = base_size + (relative_size * (max_size - base_size))
                
                chart_data.append({
                    "x": ld.get("total_matches", 0),  # Number of tournaments on x-axis
                    "y": ld.get("relative_mean_win_rate", 0),       # Win rate on y-axis
                    "r": bubble_size,       # Scaled bubble size
                    "name": card.name if card else ld.get("leader_id"),
                    "image": ld.get("image_url"),  # Add leader image URL
                    "raw_wins": ld.get("total_wins", 0)  # Store raw wins for tooltip
                })
                colors.append(leader_colors)
        
        # Create the chart (slider lives outside the swap target on the page)
        chart_div = create_bubble_chart(
            container_id="tournament-chart",
            data=chart_data,
            colors=colors,
            title=""
        )
        # Script to update external slider max based on data and keep values in range
        slider_update_script = ft.Script(f"""
            (function(){{
                const newMax = {max_matches};
                const slider = document.getElementById('tournament-match-slider');
                if (!slider) return;
                const minInput = slider.querySelector('.min-range');
                const maxInput = slider.querySelector('.max-range');
                const minValSpan = slider.querySelector('.min-value');
                const maxValSpan = slider.querySelector('.max-value');
                const track = slider.querySelector('.slider-track');
                if (!minInput || !maxInput) return;

                // Update max bounds
                const oldMax = parseInt(minInput.max || '0');
                if (oldMax !== newMax) {{
                    minInput.max = String(newMax);
                    maxInput.max = String(newMax);
                }}

                // Clamp current values within new bounds
                let minVal = parseInt(minInput.value || '0');
                let maxVal = parseInt(maxInput.value || String(newMax));
                if (maxVal > newMax) maxVal = newMax;
                if (minVal > maxVal) minVal = maxVal;
                minInput.value = String(minVal);
                maxInput.value = String(maxVal);

                // Update displayed value labels
                if (minValSpan) minValSpan.textContent = minVal.toLocaleString();
                if (maxValSpan) maxValSpan.textContent = maxVal.toLocaleString();

                // Update slider track CSS variables
                if (track) {{
                    const minBase = parseInt(minInput.min || '0');
                    const pct = (v) => ((v - minBase) / Math.max(1, (newMax - minBase))) * 100;
                    track.style.setProperty('--left-percent', pct(minVal) + '%');
                    track.style.setProperty('--right-percent', (100 - pct(maxVal)) + '%');
                }}
            }})();
        """)
        
        # If fallback was used, add notification
        if fallback_used:
            notification = create_fallback_notification(
                params.meta_format[0],  # Show first requested meta format
                effective_meta_formats[0],  # Show first effective meta format
                dropdown_id="meta-formats-select"
            )
            return ft.Div(notification, chart_div, slider_update_script)
        
        return ft.Div(chart_div, slider_update_script)

    @rt("/api/tournaments/decklist-donut")
    def get_tournament_decklist_donut(request: Request):
        """Return a donut chart for most popular tournament decklists in timeframe."""
        # Parse params
        params = TournamentPageParams(**get_query_params_as_dict(request))
        query = get_query_params_as_dict(request)
        
        days_param = query.get("days", "14")
        placing_param = query.get("placing", "all")
        
        # Get decklists filtered by meta formats and region
        decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            meta_format_region=params.region
        )

        # Filter by time window if not "all"
        if days_param != "all":
            try:
                days = int(days_param)
                since_ts = datetime.now(timezone.utc) - timedelta(days=days)
                decklists = [d for d in decklists if d.tournament_timestamp >= since_ts]
            except (TypeError, ValueError):
                # If parsing fails, use all decklists
                pass

        # Filter by tournament placing if not "all"
        if placing_param != "all":
            try:
                max_placing = int(placing_param)
                decklists = [d for d in decklists if d.placing is not None and d.placing <= max_placing]
            except (TypeError, ValueError):
                # If parsing fails, use all decklists
                pass

        # Aggregate by leader_id
        counts: dict[str,int] = defaultdict(int)
        for d in decklists:
            counts[d.leader_id] += 1

        total = sum(counts.values()) or 1

        # Map to names/colors/images
        card_data = get_card_id_card_data_lookup()
        leader_data = get_leader_extended(meta_formats=MetaFormat.to_list(region=params.region))
        leader_extended_dict = {le.id: le for le in leader_data}
        
        labels: list[str] = []
        values: list[int] = []
        colors: list[str] = []  # This will now contain arrays of colors for multi-color leaders
        images: list[str] = []
        leader_ids: list[str] = []

        # Sort by count desc and show all leaders (no "Others" category)
        sorted_items = sorted(counts.items(), key=lambda x: x[1], reverse=True)

        for lid, v in sorted_items:
            card = card_data.get(lid)
            leader = leader_extended_dict.get(lid)
            labels.append(card.name if card else lid)
            values.append(v)
            leader_ids.append(lid)
            
            # Get leader image (prefer AA version)
            image_url = ""
            if leader:
                image_url = leader.aa_image_url or leader.image_url or ""
            images.append(image_url)
            
            # Create color data for multi-color support
            if card and card.colors:
                # For multi-color leaders, pass array of hex colors
                leader_colors = [color.to_hex_color() for color in card.colors]
                colors.append(leader_colors)
            else:
                # Single color fallback
                colors.append(["#808080"])

        # Compute subtitle based on timeframe and placing
        placing_text = ""
        if placing_param != "all":
            placing_text = f" (Top {placing_param})"
        
        if days_param == "all":
            subtitle = f"{total} decklists{placing_text} (all available)"
        else:
            subtitle = f"{total} decklists{placing_text} in last {days_param} days"

        # Create donut chart using the new unified chart function
        container_id = "tournament-decklist-donut-canvas"
        
        return ft.Div(
            ft.Div(
                ft.P(subtitle, cls="text-gray-300 text-sm mb-2"),
                cls="mb-2"
            ),
            create_donut_chart(
                container_id=container_id,
                labels=labels,
                values=values,
                colors=colors,
                images=images,
                leader_ids=leader_ids
            ),
            cls="bg-gray-800/30 rounded-lg px-4"
        )

    @rt("/api/tournaments/decklist-donut-colors")
    def get_tournament_decklist_donut_colors(request: Request):
        """Return a donut chart aggregated by leader colors (multi-colored leaders count in each color)."""
        # Parse params
        params = TournamentPageParams(**get_query_params_as_dict(request))
        query = get_query_params_as_dict(request)
        
        days_param = query.get("days", "14")
        placing_param = query.get("placing", "all")
        
        # Get decklists filtered by meta formats and region
        decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            meta_format_region=params.region
        )

        # Filter by time window if not "all"
        if days_param != "all":
            try:
                days = int(days_param)
                since_ts = datetime.now(timezone.utc) - timedelta(days=days)
                decklists = [d for d in decklists if d.tournament_timestamp >= since_ts]
            except (TypeError, ValueError):
                pass

        # Filter by tournament placing if not "all"
        if placing_param != "all":
            try:
                max_placing = int(placing_param)
                decklists = [d for d in decklists if d.placing is not None and d.placing <= max_placing]
            except (TypeError, ValueError):
                pass

        # Aggregate counts by color
        color_counts: dict[str, int] = defaultdict(int)
        # Also assemble display metadata
        color_to_hex: dict[str, str] = {}

        card_data = get_card_id_card_data_lookup()

        for d in decklists:
            card = card_data.get(d.leader_id)
            if not card or not card.colors:
                continue
            for c in card.colors:
                color_name = str(c)
                color_counts[color_name] += (1/len(card.colors))
                color_to_hex[color_name] = c.to_hex_color()

        # Map to lists sorted by count desc
        sorted_items = sorted(color_counts.items(), key=lambda x: x[1], reverse=True)
        labels: list[str] = [name for name, _ in sorted_items]
        values: list[int] = [cnt for _, cnt in sorted_items]
        colors: list[str] = [[color_to_hex[name]] for name in labels]  # wrap as single-color arrays for chart
        images: list[str] = [""] * len(labels)
        leader_ids: list[str] = labels

        total = sum(values) or 1
        placing_text = ""
        if placing_param != "all":
            placing_text = f" (Top {placing_param})"
        if days_param == "all":
            subtitle = f"{total} decklists by color{placing_text} (all available)"
        else:
            subtitle = f"{total} decklists by color{placing_text} in last {days_param} days"

        container_id = "tournament-decklist-donut-canvas"
        return ft.Div(
            ft.Div(
                ft.P(subtitle, cls="text-gray-300 text-sm mb-2"),
                cls="mb-2"
            ),
            create_donut_chart(
                container_id=container_id,
                labels=labels,
                values=values,
                colors=colors,
                images=images,
                leader_ids=leader_ids
            ),
            cls="bg-gray-800/30 rounded-lg px-4"
        )

    @rt("/api/tournaments/decklist-donut-smart")
    def get_tournament_decklist_donut_smart(request: Request):
        """Smart router that delegates to either leaders or colors endpoint based on view_mode parameter."""
        # Get view_mode parameter
        query = get_query_params_as_dict(request)
        view_mode = query.get("view_mode", "leaders")
        
        # Route to appropriate endpoint
        if view_mode == "colors":
            return get_tournament_decklist_donut_colors(request)
        else:
            return get_tournament_decklist_donut(request)

    @rt("/api/leader-tournaments")
    async def get_leader_tournaments(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        
        # Get tournament data
        tournament_decklists = get_tournament_decklist_data(
            meta_formats=params.meta_format,
            leader_ids=[params.lid]
        )
        tournaments = get_all_tournament_extened_data(meta_formats=params.meta_format)
        
        # Get leader data
        leader_data = get_leader_extended()
        leader_extended_dict = {le.id: le for le in leader_data}
        
        # Create and return the tournament section
        return create_tournament_section(
            leader_id=params.lid,
            tournament_decklists=tournament_decklists,
            tournaments=tournaments,
            leader_extended_dict=leader_extended_dict,
            hx_include=HX_INCLUDE
        )

    @rt("/api/tournaments/all")
    def get_all_tournaments(request: Request):
        """Return all tournaments with basic information."""
        # Parse params using Pydantic model
        params = TournamentPageParams(**get_query_params_as_dict(request))
        
        # Get tournament data
        tournaments = get_all_tournament_extened_data(meta_formats=params.meta_format)
        
        # Filter by region if specified
        if params.region != MetaFormatRegion.ALL:
            tournaments = [t for t in tournaments if t.meta_format_region == params.region]
            
        # Sort tournaments by date, newest first
        tournaments.sort(key=lambda x: x.tournament_timestamp, reverse=True)
        
        # Create tournament select options
        tournament_options = []
        for t in tournaments:
            tournament_options.append(
                ft.Option(
                    f"{t.name} ({t.tournament_timestamp.strftime('%Y-%m-%d')})",
                    value=t.id,
                    cls="text-white"
                )
            )

        # Get the first tournament's details for initial display
        first_tournament_id = tournaments[0].id if tournaments else None
        
        return ft.Div(
            # Tournament selector
            ft.Div(
                ft.Select(
                    *tournament_options,
                    id="tournament-select",
                    name="tournament_id",
                    cls="styled-select",
                    hx_get="/api/tournament-details",
                    hx_target="#tournament-details",
                    hx_trigger="change",
                    hx_include="[name='meta_format'],[name='region']",
                    hx_indicator="#tournament-selector-loading"
                ),
                cls="mb-4"
            ),
            # Loading spinner positioned right below the selector
            create_loading_spinner(
                id="tournament-selector-loading",
                size="w-8 h-8",
                container_classes="min-h-[60px] mb-4"
            ),
            # Tournament details container
            ft.Div(
                # Initial content for the first tournament
                hx_get="/api/tournament-details",
                hx_trigger="load",
                hx_include="[name='meta_format'],[name='region']",
                hx_vals={"tournament_id": first_tournament_id} if first_tournament_id else None,
                id="tournament-details",
                cls="space-y-6"
            ),
            cls="space-y-8"
        )

    @rt("/api/tournament-details")
    async def get_tournament_details(request: Request):
        """Get details for a specific tournament."""
        params_dict = get_query_params_as_dict(request)
        tournament_id = params_dict.get("tournament_id")
        params = TournamentPageParams(**params_dict)

        if not tournament_id:
            return ft.P("No tournament selected", cls="text-gray-400")
            
        # Get tournament data
        tournaments = get_all_tournament_extened_data(
            meta_formats=params.meta_format,
        )
        tournament = next((t for t in tournaments if t.id == tournament_id), None)
        
        if not tournament:
            return ft.P("Tournament not found", cls="text-red-400")
            
        
        # Get tournament decklists
        tournament_decklists = get_tournament_decklist_data(params.meta_format)
        tournament_decklists = [td for td in tournament_decklists if td.tournament_id == tournament_id]
        
        # Get winner decklist for fallback
        winner_decklist = next((td for td in tournament_decklists if td.placing == 1), None)
        
        # Calculate leader participation stats
        leader_stats = {}
        if tournament.num_players:
            for lid, placings in tournament.leader_ids_placings.items():
                leader_stats[lid] = len(placings) / tournament.num_players
                
        # Get leader data for images
        leader_data = get_leader_extended()
        leader_extended_dict = {le.id: le for le in leader_data}
        if winner_decklist and winner_decklist.leader_id in leader_extended_dict:
            leader_image_url = leader_extended_dict[winner_decklist.leader_id].aa_image_url if leader_extended_dict[winner_decklist.leader_id].aa_image_url else leader_extended_dict[winner_decklist.leader_id].image_url
        else:
            leader_image_url = None
            
        # Set default selected leader (winner)
        selected_leader_id = winner_decklist.leader_id if winner_decklist else None
        
        # Create the tournament details view with new layout
        return ft.Div(
            id="tournament-leader-content",
            hx_get="/api/tournament-select-leader",
            hx_trigger="load",
            hx_include="[name='meta_format'],[name='region']",
            hx_vals={
                "tournament_id": tournament_id,
                "selected_leader_id": selected_leader_id
            } if selected_leader_id else None,
            cls="space-y-6"
        ) 

    @rt("/api/tournament-select-leader")
    async def get_tournament_leader_content(request: Request):
        """Get tournament content with selected leader highlighted."""
        def _create_leader_decklist_section(leader_decklists, selected_index, card_data, meta_format, 
                                          tournament_id, leader_id, fallback_decklist):
            """Create the decklist section for the selected leader."""
            if not leader_decklists:
                # Fallback to winner's decklist if no leader decklists available
                if fallback_decklist:
                    return ft.Div(
                        ft.H4("Winner's Decklist (No decklist found for selected leader)", cls="text-lg font-bold text-white mb-4"),
                        create_decklist_view(
                            fallback_decklist.decklist,
                            card_data,
                            title=None,  # Title already shown above
                            meta_format=meta_format,
                            currency=CardCurrency.EURO
                        )
                    )
                else:
                    return ft.P("No decklist available", cls="text-gray-400")
            
            # Get the selected decklist
            if selected_index >= len(leader_decklists):
                selected_index = 0
            
            selected_decklist = leader_decklists[selected_index]
            
            # Create title based on placing
            title_parts = []
            if selected_decklist.placing == 1:
                title_parts.append("Winner's Decklist")
            elif selected_decklist.placing is not None:
                title_parts.append(f"#{selected_decklist.placing} Decklist")
            else:
                title_parts.append("Decklist")
            
            if selected_decklist.player_id:
                title_parts.append(f"({selected_decklist.player_id})")
            
            title = " ".join(title_parts)
            
            # Create decklist selector if multiple decklists
            decklist_selector = create_decklist_selector(
                leader_decklists, 
                selected_index, 
                tournament_id, 
                leader_id
            )
            
            # Build components list, filtering out None values
            components = [ft.H4(title, cls="text-lg font-bold text-white mb-4")]
            
            if decklist_selector:
                components.append(decklist_selector)
                
            components.append(
                create_decklist_view(
                    selected_decklist.decklist,
                    card_data,
                    title=None,  # Title already shown above
                    meta_format=meta_format,
                    currency=CardCurrency.EURO
                )
            )
            
            return ft.Div(*components, cls="space-y-4")
        
        params_dict = get_query_params_as_dict(request)
        tournament_id = params_dict.get("tournament_id")
        selected_leader_id = params_dict.get("selected_leader_id")
        selected_decklist_index = int(params_dict.get("selected_decklist_index", "0"))
        params = TournamentPageParams(**params_dict)

        if not tournament_id:
            return ft.P("No tournament selected", cls="text-gray-400")
            
        # Get tournament data
        tournaments = get_all_tournament_extened_data(
            meta_formats=params.meta_format,
        )
        tournament = next((t for t in tournaments if t.id == tournament_id), None)
        
        if not tournament:
            return ft.P("Tournament not found", cls="text-red-400")
            
        # Get card and leader data
        card_id2card_data = get_card_id_card_data_lookup()
        leader_data = get_leader_extended(meta_formats=MetaFormat.to_list(region=params.region))
        leader_extended_dict = {le.id: le for le in leader_data}
        
        # Get tournament decklists
        tournament_decklists = get_tournament_decklist_data(params.meta_format)
        tournament_decklists = [td for td in tournament_decklists if td.tournament_id == tournament_id]
        
        # Get winner decklist
        winner_decklist = next((td for td in tournament_decklists if td.placing == 1), None)
        
        # Calculate leader participation stats
        leader_stats = {}
        if tournament.num_players:
            for lid, placings in tournament.leader_ids_placings.items():
                leader_stats[lid] = len(placings) / tournament.num_players
        
        # Set default selected leader if none provided
        if not selected_leader_id:
            selected_leader_id = winner_decklist.leader_id if winner_decklist else None
        
        # Get selected leader's decklists
        selected_leader_decklists = []
        if selected_leader_id:
            selected_leader_decklists = [td for td in tournament_decklists if td.leader_id == selected_leader_id]
            # Sort by placing (best placing first)
            selected_leader_decklists.sort(key=lambda x: x.placing if x.placing is not None else 999)
        
        # Get selected leader info for display
        selected_leader_data = leader_extended_dict.get(selected_leader_id) if selected_leader_id else None
        selected_leader_image = None
        if selected_leader_data:
            selected_leader_image = selected_leader_data.aa_image_url or selected_leader_data.image_url
        
        # Get match data for selected leader
        matches = []
        if selected_leader_id:
            matches = get_tournament_match_data(
                tournament_id=tournament_id,
                leader_id=selected_leader_id
            )
        
        return ft.Div(
            ft.Div(
                # Left Column: Tournament Facts, Selected Leader Image, and Match Progression
                ft.Div(
                    # Tournament facts
                    create_tournament_keyfacts(
                        tournament,
                        winner_name=winner_decklist.leader_id if winner_decklist else "Unknown"
                    ),
                    
                    # Selected Leader Image
                    ft.Div(
                        ft.H5(
                            f"Selected Leader{' (Winner)' if selected_leader_id and winner_decklist and selected_leader_id == winner_decklist.leader_id else ''}", 
                            cls="text-lg font-bold text-white mb-2"
                        ) if selected_leader_id else None,
                        ft.Img(
                            src=selected_leader_image,
                            cls="w-full h-auto rounded-lg shadow-lg max-w-[300px] mx-auto"
                        ) if selected_leader_image else ft.P("No leader selected", cls="text-gray-400 text-center"),
                        cls="mt-6 mb-6"
                    ),
                    
                    # Match Progression (moved here)
                    ft.Div(
                        ft.H5("Match Progression", cls="text-lg font-bold text-white mb-4"),
                        create_loading_spinner(
                            id="tournament-leader-loading",
                            size="w-6 h-6",
                            container_classes="min-h-[50px]"
                        ),
                        create_match_progression(
                            matches=matches,
                            leader_extended_dict=leader_extended_dict,
                            cid2cdata_dict=card_id2card_data,
                            selected_leader_id=selected_leader_id or ""
                        ) if selected_leader_id else ft.P("Click on a leader above to see their match progression", cls="text-gray-400"),
                        cls="bg-gray-800 rounded-lg p-4"
                    ),
                    
                    cls="w-full lg:w-1/3 space-y-6"
                ),
                
                # Right Column: Leader Participation and Decklist
                ft.Div(
                    # Leader participation section (now clickable)
                    ft.Div(
                        ft.H4("Leader Participation (Click to Select)", cls="text-lg font-bold text-white mb-4"),
                        create_leader_grid(
                            leader_stats, 
                            leader_extended_dict, 
                            card_id2card_data, 
                            selected_leader_id=selected_leader_id,
                            tournament_id=tournament_id
                        )
                    ),
                    
                    # Decklist section
                    ft.Div(
                        _create_leader_decklist_section(
                            selected_leader_decklists,
                            selected_decklist_index,
                            card_id2card_data,
                            params.meta_format[0],
                            tournament_id,
                            selected_leader_id,
                            winner_decklist
                        ),
                        cls="mt-8"
                    ),
                    cls="w-full lg:w-2/3 lg:pl-8 mt-8 lg:mt-0"
                ),
                cls="flex flex-col lg:flex-row gap-8"
            ),
            cls="space-y-6"
        )
