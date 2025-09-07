from collections import defaultdict
from fasthtml import ft
from starlette.requests import Request
from op_tcg.backend.models.leader import LeaderExtended, LeaderboardSortBy
from op_tcg.backend.models.input import MetaFormat, MetaFormatRegion
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend_fasthtml.utils.extract import (
    get_card_data, 
    get_leader_extended, 
    get_card_popularity_data, 
    get_card_id_card_data_lookup
)
from op_tcg.frontend_fasthtml.pages.home import create_leaderboard_table
from op_tcg.frontend_fasthtml.utils.filter import filter_leader_extended, get_leaders_with_decklist_data
from op_tcg.frontend_fasthtml.utils.api import get_query_params_as_dict, get_filtered_leaders, get_effective_meta_format_with_fallback, create_fallback_notification
from op_tcg.frontend_fasthtml.pages.leader import create_leader_content, HX_INCLUDE
from op_tcg.frontend_fasthtml.pages.tournaments import create_tournament_content
from op_tcg.frontend_fasthtml.pages.card_popularity import create_card_popularity_content
from op_tcg.frontend_fasthtml.api.models import LeaderboardFilter, LeaderboardSort, LeaderDataParams, TournamentPageParams, CardPopularityParams
from op_tcg.frontend_fasthtml.components.card_modal import create_card_modal

def filter_cards(cards_data: list, params: CardPopularityParams) -> list:
    """Filter cards based on the provided parameters.
    
    Args:
        cards_data: List of card data objects
        params: CardPopularityParams object containing filter criteria
        
    Returns:
        Filtered list of cards
    """
    filtered_cards = []
    
    for card in cards_data:
        # Skip if card is from a newer meta format
        if card.meta_format and MetaFormat.to_list().index(card.meta_format) > MetaFormat.to_list().index(params.meta_format):
            continue
            
        # Filter by search term
        if params.search_term:
            search_terms = [term.strip().lower() for term in params.search_term.split(";")]
            if not all(term in card.get_searchable_string().lower() for term in search_terms):
                continue
            
        # Filter by colors
        if not any(color in params.card_colors for color in card.colors):
            continue
            
        # Filter by attributes
        if params.card_attributes and not any(attr in params.card_attributes for attr in card.attributes):
            continue
            
        # Filter by card category
        if params.card_category and card.card_category not in params.card_category:
            continue
            
        # Filter by counter
        if params.card_counter == 0 and card.counter not in [None, 0]:
            continue

        elif params.card_counter not in [0, None] and card.counter != params.card_counter:
            continue

        # Filter by card types
        if params.card_types and not any(t in params.card_types for t in card.types):
            continue
            
        # Filter by cost range
        if card.cost is not None and not (params.min_cost <= card.cost <= params.max_cost):
            continue
            
        # Filter by power range
        if card.power is not None and not (params.min_power * 1000 <= card.power <= params.max_power * 1000):
            continue
            
        # Filter by price range
        if params.currency == CardCurrency.EURO and card.latest_eur_price:
            if not (params.min_price <= card.latest_eur_price <= params.max_price):
                continue
        elif params.currency == CardCurrency.US_DOLLAR and card.latest_usd_price:
            if not (params.min_price <= card.latest_usd_price <= params.max_price):
                continue
                
        # Filter by abilities
        if params.card_abilities or params.ability_text:
            if params.filter_operator == "OR":
                if not (any(ability in card.ability for ability in (params.card_abilities or [])) or 
                       (params.ability_text and params.ability_text.lower() in card.ability.lower())):
                    continue
            else:  # AND
                if not (all(ability in card.ability for ability in (params.card_abilities or [])) and 
                       (not params.ability_text or params.ability_text.lower() in card.ability.lower())):
                    continue
        
        filtered_cards.append(card)
    
    return filtered_cards

def setup_api_routes(rt):
    @rt("/api/tournament-content")
    def get_tournament_content(request: Request):
        """Return the tournament page content."""
        # Parse params using Pydantic model
        params = TournamentPageParams(**get_query_params_as_dict(request))
        return create_tournament_content()

    @rt("/api/leaderboard")
    def api_leaderboard(request: Request):
        # Parse the sort and meta format parameters
        sort_params = LeaderboardSort(**get_query_params_as_dict(request))
        filter_params = LeaderboardFilter(**get_query_params_as_dict(request))
        
        # Get filtered leaders
        leader_extended_data: list[LeaderExtended] = get_leader_extended(meta_format_region=get_query_params_as_dict(request).get("region"))
        filtered_leaders = get_filtered_leaders(request, leader_extended_data=leader_extended_data)
        
        # Use utility function to get effective meta format with fallback
        effective_meta_format, fallback_used = get_effective_meta_format_with_fallback(
            sort_params.meta_format, 
            filtered_leaders
        )
        
        display_name2df_col_name = {
            "Name": "name",
            "Set": "id",
            LeaderboardSortBy.TOURNAMENT_WINS: "tournament_wins",
            LeaderboardSortBy.MATCH_COUNT: "total_matches",
            LeaderboardSortBy.WIN_RATE: "win_rate",
            LeaderboardSortBy.DOMINANCE_SCORE: "d_score",
            LeaderboardSortBy.ELO: "elo"
        }

        # Sort leaders by the specified sort criteria
        if sort_params.sort_by == LeaderboardSortBy.TOURNAMENT_WINS:
            filtered_leaders.sort(key=lambda x: (x.tournament_wins > 0, x.tournament_wins, x.elo or 0), reverse=True)
        else:
            # Handle None values in sorting by providing default values
            def get_sort_key(leader):
                attr_name = display_name2df_col_name.get(sort_params.sort_by)
                value = getattr(leader, attr_name)
                # Return 0 for None values to sort them to the end
                return value if value is not None else 0
            
            filtered_leaders.sort(key=get_sort_key, reverse=True)
        
        # Create the leaderboard table using the effective meta format
        table_content = create_leaderboard_table(
            filtered_leaders,
            leader_extended_data,
            effective_meta_format,
            region=filter_params.region
        )
        # If fallback was used, add a notification message
        if fallback_used:
            notification = create_fallback_notification(
                sort_params.meta_format,
                effective_meta_format
            )
            return ft.Div(notification, table_content)
        
        return table_content

    @rt("/api/leader-data")
    async def get_leader_data(request: Request):
        # Parse params using Pydantic model
        params = LeaderDataParams(**get_query_params_as_dict(request))
        match_data_exists = True

        # Get leader data with meta format region filtering
        if params.lid:
            # If a leader ID is provided, get data for that specific leader
            leader_data = get_leader_extended(
                leader_ids=[params.lid],
                meta_format_region=params.region
            )
        else:
            # Otherwise, get all leaders and find the one with highest d_score
            leader_data = get_leader_extended(meta_format_region=params.region)
            
        # Filter by meta format and apply additional filters
        filtered_by_meta = [l for l in leader_data if l.meta_format in params.meta_format]
        
        # Get leaders that have decklist data in these meta formats
        leaders_with_decklists = get_leaders_with_decklist_data(params.meta_format)
        
        # Apply standard filtering
        filtered_data = filter_leader_extended(
            leaders=filtered_by_meta,
            only_official=params.only_official
        )
        
        # Create a set of leader IDs that are already included in filtered_data
        already_included_ids = {fl.id for fl in filtered_data}
        
        # Add leaders that have decklist data but might not have match data
        # Only include if they are not already in the filtered_data set
        additional_leaders_with_decklist = [
            l for l in filtered_by_meta 
            if l.id in leaders_with_decklists and l.id not in already_included_ids
        ]
        
        # Combine both sets of leaders
        all_filtered_data = filtered_data + additional_leaders_with_decklist
        
        # If no match data exists, but the leader has decklist data, use the latest leader data
        if not all_filtered_data and params.lid in leaders_with_decklists:
            all_filtered_data = filter_leader_extended(
                leaders=[l for l in leader_data if l.id == params.lid],
                only_official=params.only_official
            )
            match_data_exists = False

        
        # Data found for requested meta formats - no fallback needed
        if params.lid:
            # Find the specific leader
            leader_data_result = next((l for l in all_filtered_data if l.id == params.lid), None)
            if not leader_data_result:
                return ft.P("No data available for this leader in the selected meta format.", cls="text-red-400")
        else:
            # Get the top leader
            all_filtered_data.sort(key=lambda x: (x.d_score or 0, x.elo or 0), reverse=True)
            leader_data_result = all_filtered_data[0]
        
        return create_leader_content(
            leader_id=leader_data_result.id,
            leader_name=leader_data_result.name,
            aa_image_url=leader_data_result.aa_image_url,
            total_matches=leader_data_result.total_matches if match_data_exists else None
        )

    @rt("/api/card-popularity")
    def get_card_popularity(request: Request):
        """Return the card popularity content with filtered cards."""
        # Parse params using Pydantic model
        params = CardPopularityParams(**get_query_params_as_dict(request))
        
        # Get card data and popularity data
        card_data_lookup = get_card_id_card_data_lookup()
        card_popularity_list = get_card_popularity_data()
        
        # Use utility function to get effective meta format with fallback
        effective_meta_format, fallback_used = get_effective_meta_format_with_fallback(
            params.meta_format,
            card_popularity_list
        )
        
        # Filter card popularity data by effective meta format
        card_popularity_dict = {}
        for cp in card_popularity_list:
            if cp.meta_format == effective_meta_format:
                if cp.card_id not in card_popularity_dict:
                    card_popularity_dict[cp.card_id] = []
                card_popularity_dict[cp.card_id].append(cp.popularity)
        card_popularity_dict = {
            cid: max(popularity_list) 
            for cid, popularity_list in card_popularity_dict.items() 
        }
        
        # Get all cards and apply filters (update params to use effective meta format)
        params.meta_format = effective_meta_format
        cards_data = list(card_data_lookup.values())
        filtered_cards = filter_cards(cards_data, params)
        
        # Sort cards by popularity
        filtered_cards.sort(
            key=lambda x: card_popularity_dict.get(x.id, 0),
            reverse=True
        )
        
        # Create the card popularity content
        content = create_card_popularity_content(
            filtered_cards, 
            card_popularity_dict, 
            params.page, 
            search_term=params.search_term, 
            currency=params.currency
        )
        
        # If fallback was used, add notification
        if fallback_used:
            # Get the original requested meta format
            original_params = CardPopularityParams(**get_query_params_as_dict(request))
            notification = create_fallback_notification(
                original_params.meta_format,
                effective_meta_format,
                dropdown_id="meta-format-select"
            )
            return ft.Div(notification, content)
        
        return content

    @rt("/api/card-modal")
    def get_card_modal(request: Request):
        """Return the card modal content."""
        card_id = request.query_params.get("card_id")
        meta_format = request.query_params.get("meta_format")
        currency = request.query_params.get("currency")
        
        if not card_id:
            return ft.Div("No card ID provided", cls="text-red-400")
            
        if not meta_format:
            return ft.Div("No meta format provided", cls="text-red-400")
            
        # Get all versions of the card
        card_data = get_card_data()
        base_card = None
        card_versions = []
        for card in card_data:
            if card.id == card_id:
                if card.aa_version == 0:
                    base_card = card
                    continue
                card_versions.append(card)

        if not base_card:
            return ft.Div("Card not found", cls="text-red-400")
        
        # Sort versions by ID to ensure consistent order
        card_versions.sort(key=lambda x: x.aa_version)
            
        # Get card popularity for the specific meta format
        card_popularity_list = get_card_popularity_data()
        popularity = 0
        for cp in card_popularity_list:
            if cp.card_id == card_id and cp.meta_format == meta_format:
                popularity = max(popularity, cp.popularity)

        # Find adjacent cards in the grid
        card_elements = request.query_params.getlist("card_elements")
        current_index = -1
        prev_card_id = None
        next_card_id = None

        if card_elements:
            try:
                current_index = card_elements.index(card_id)
                if current_index > 0:
                    prev_card_id = card_elements[current_index - 1]
                if current_index < len(card_elements) - 1:
                    next_card_id = card_elements[current_index + 1]
            except ValueError:
                pass
        
        # Create and return modal using the component
        return create_card_modal(base_card, card_versions, popularity, currency, prev_card_id, next_card_id, card_elements) 