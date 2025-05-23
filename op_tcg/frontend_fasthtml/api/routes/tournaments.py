from collections import defaultdict
from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.leader import LeaderExtended
from op_tcg.frontend.utils.extract import get_tournament_decklist_data, get_all_tournament_extened_data
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict
from op_tcg.frontend_fasthtml.utils.extract import (
    get_leader_extended,
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.components.tournament import (
    create_tournament_section,
    create_tournament_keyfacts,
    create_leader_grid
)
from op_tcg.frontend_fasthtml.components.tournament_decklist import create_decklist_view
from op_tcg.frontend_fasthtml.api.models import LeaderDataParams, TournamentPageParams
from op_tcg.frontend_fasthtml.pages.leader import HX_INCLUDE
from op_tcg.frontend_fasthtml.utils.charts import create_bubble_chart
import json

def aggregate_leader_data(leader_data: list[LeaderExtended]):
    """Aggregate leader data by leader_id and calculate relative mean win rate."""
    aggregated_data = defaultdict(lambda: {
        "total_matches": [],
        "total_wins": [],
        "win_rate": [],
        "image_url": ""
    })
    
    for ld in leader_data:
        aggregated_data[ld.id]["total_matches"].append(ld.total_matches)
        aggregated_data[ld.id]["total_wins"].append(ld.tournament_wins)
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

    @rt("/api/tournaments/chart")
    def get_tournament_chart(request: Request):
        """Return the tournament statistics chart."""
        # Parse params using Pydantic model
        params = TournamentPageParams(**get_query_params_as_dict(request))
        
        # Get leader data
        leader_data = get_leader_extended(meta_format_region=params.region)
        card_data = get_card_id_card_data_lookup()
        
        # Filter by meta formats
        leader_data = [ld for ld in leader_data if ld.meta_format in params.meta_format and ld.only_official]

        # Calculate relative mean win rate and prepare final data for chart
        final_leader_data = aggregate_leader_data(leader_data)
        
        # Process data for bubble chart
        chart_data = []
        colors = []
        
        # First pass to get max values for scaling
        max_tournament_wins = max((ld.get("total_wins", 0) for ld in final_leader_data), default=1)
        
        # Calculate bubble size scaling factor based on number of data points
        base_size = 5  # Minimum bubble size
        max_size = 35 if len(final_leader_data) > 20 else 50  # Smaller max size for larger datasets
        
        for ld in final_leader_data:
            if ld.get("total_matches", 0) is None:
                continue
            if ld.get("total_matches", 0) > 0:  # Only include leaders with matches
                card = card_data.get(ld.get("leader_id"))
                color = card.to_hex_color() if card else "#808080"
                
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
                colors.append(color)
        
        # Create and return the chart
        return create_bubble_chart(
            container_id="tournament-chart",
            data=chart_data,
            colors=colors,
            title="Leader Tournament Popularity"
        )

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
        
        # Get card data
        card_id2card_data = get_card_id_card_data_lookup()
        
        # Create and return the tournament section
        return create_tournament_section(
            leader_id=params.lid,
            tournament_decklists=tournament_decklists,
            tournaments=tournaments,
            leader_extended_dict=leader_extended_dict,
            cid2cdata_dict=card_id2card_data,
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
                    hx_include="[name='meta_format'],[name='region']"
                ),
                cls="mb-8"
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
            
        # Get card data
        card_id2card_data = get_card_id_card_data_lookup()
        
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
                
        # Get leader data for images
        leader_data = get_leader_extended()
        leader_extended_dict = {le.id: le for le in leader_data}
        if winner_decklist and winner_decklist.leader_id in leader_extended_dict:
            leader_image_url = leader_extended_dict[winner_decklist.leader_id].aa_image_url if leader_extended_dict[winner_decklist.leader_id].aa_image_url else leader_extended_dict[winner_decklist.leader_id].image_url
        else:
            leader_image_url = None
            
        # Create the tournament details view with two columns
        return ft.Div(
            ft.Div(
                # Tournament Facts and Winner Image Section
                ft.Div(
                    # Tournament facts
                    create_tournament_keyfacts(
                        tournament,
                        winner_name=winner_decklist.leader_id if winner_decklist else "Unknown"
                    ),
                    
                    # Winner Leader Image (if available)
                    ft.Div(
                        ft.Img(
                            src=leader_image_url if winner_decklist else None,
                            cls="w-full h-auto rounded-lg shadow-lg max-w-[300px] mx-auto"
                        ) if winner_decklist and winner_decklist.leader_id in card_id2card_data else ft.P("No winner image available", cls="text-gray-400"),
                        cls="mt-6"
                    ),
                    cls="w-full lg:w-1/3"
                ),
                
                # Leader Stats and Decklist Section
                ft.Div(
                    # Leader participation section
                    ft.Div(
                        ft.H4("Leader Participation", cls="text-lg font-bold text-white mb-4"),
                        create_leader_grid(leader_stats, leader_extended_dict, card_id2card_data)
                    ),
                    
                    # Winner decklist section
                    ft.Div(
                        create_decklist_view(
                            winner_decklist.decklist if winner_decklist else {},
                            card_id2card_data,
                            title="Winner's Decklist"
                        ) if winner_decklist else ft.P("No winner decklist available", cls="text-gray-400"),
                        cls="mt-8"
                    ),
                    cls="w-full lg:w-2/3 lg:pl-8 mt-8 lg:mt-0"
                ),
                cls="flex flex-col lg:flex-row gap-8"
            ),
            cls="space-y-6"
        ) 