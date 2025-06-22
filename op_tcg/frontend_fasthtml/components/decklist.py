from fasthtml import ft
from op_tcg.backend.models.cards import ExtendedCardData, OPTcgLanguage, LatestCardPrice
from op_tcg.frontend_fasthtml.utils.decklist import DecklistData, decklist_to_export_str, ensure_leader_id

# Added for styling the select component, consider moving to a common utils/constants
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def add_card_modal():
    """Add a card modal to the page for displaying card images with navigation."""
    return ft.Div(
        # Modal container similar to the original implementation
        ft.Div(
            # Close button
            ft.Span("×", cls="decklist-modal-close", onclick="closeDecklistModal()"),
            
            # Image
            ft.Img(id="decklist-modal-img", cls="decklist-modal-image"),
            
            id="decklistModal", 
            cls="decklist-modal"
        )
    )

def display_card_list(decklist_data: DecklistData, card_ids: list[str]):
    """
    Display a list view of cards from the decklist using fasthtml components.
    
    Args:
        decklist_data: Aggregated decklist data
        card_ids: List of card IDs to display
    
    Returns:
        A Div containing the styled card list
    """
    # Handle empty card list
    if not card_ids:
        return ft.Div(
            ft.P("No cards found matching the criteria", cls="text-white"),
            cls="mt-4"
        )
    
    # Create card list items
    list_items = []
    
    # Include all cards with at least 2% occurrence
    filtered_cards = [cid for cid in card_ids if decklist_data.card_id2occurrence_proportion[cid] >= 0.02]
    
    for i, card_id in enumerate(filtered_cards):
        card_data = decklist_data.card_id2card_data.get(card_id)
        op_set = card_id.split("-")[0]
        occurrence_percentage = decklist_data.card_id2occurrence_proportion[card_id]
        
        # Get card image URL
        img_src = card_data.image_url if card_data else f'https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp'
        
        # Get card name
        card_name = card_data.name if card_data else card_id
        if len(card_name) > 25:
            card_name = card_name[:20] + " [...]"
            
        # Get price info if available
        price_item = None
        if card_data and hasattr(card_data, 'latest_eur_price') and hasattr(card_data, 'latest_usd_price'):
            price_item = ft.Li(f"Price: {card_data.latest_eur_price}€ | ${card_data.latest_usd_price}")
        
        # Create list item
        list_items.append(
            ft.Li(
                ft.Div(
                    ft.Img(src=img_src, alt=f"Card {card_id}"),
                    cls="decklist-image",
                    data_index=str(i),
                    onclick="openDecklistModal(this)"
                ),
                ft.Div(
                    ft.H2(card_name, cls="decklist-title"),
                    ft.Ul(
                        ft.Li(f"Card ID: {card_id}"),
                        ft.Li(f"Occurrence: {int(occurrence_percentage * 100)}%"),
                        ft.Li(f"Average Count in Deck: {decklist_data.card_id2avg_count_card[card_id]} ({round(decklist_data.card_id2avg_count_card[card_id])})"),
                        price_item,
                        cls="decklist-facts"
                    ),
                    cls="decklist-details"
                ),
                ft.Div(
                    f"{int(occurrence_percentage * 100)}%",
                    cls="decklist-circle",
                    style=f"background: rgba(123, 237, 159, {occurrence_percentage})"
                ),
                cls="decklist-item"
            )
        )
    
    # Return styled component with scrollable container
    return ft.Div(
        ft.H3("Most Common Cards", cls="text-xl font-bold text-white mb-4"),
        
        # Scrollable container with list items
        ft.Div(
            ft.Ul(*list_items, cls="decklist-list-view"),
            add_card_modal(),
            cls="decklist-list-container",
            style="max-height: 500px; overflow-y: auto; margin-bottom: 20px;"  # Scrollable container
        ),
        
        cls="mb-8"  # Added extra margin for spacing
    )

def display_decklist(decklist: dict[str, int], card_id2card_data: dict[str, ExtendedCardData], leader_id: str = None):
    """
    Display a visual representation of a complete decklist.
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        leader_id: Leader card ID to exclude from the display
    
    Returns:
        A Div containing the decklist cards
    """
    # Filter out leader card if specified
    filtered_decklist = {k: v for k, v in decklist.items() if k != leader_id} if leader_id else decklist
    
    # Create card items
    card_items = []
    
    # Get the starting index for the complete decklist images
    # This should be after the common cards list
    starting_index = 1000  # Using a high number to avoid overlap with the common cards list
    
    for i, (card_id, count) in enumerate(filtered_decklist.items()):
        # Extract set code from card_id
        op_set = card_id.split("-")[0]
        img_url = card_id2card_data[card_id].image_url if card_id in card_id2card_data else f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
        
        card_items.append(
            ft.Div(
                ft.Div(
                    ft.Img(src=img_url, cls="w-full rounded-lg"),
                    cls="cursor-pointer",
                    data_index=str(starting_index + i),
                    onclick="openDecklistModal(this)"
                ),
                ft.P(f"x{count}", cls="text-center text-white font-bold text-lg mt-2"),
                cls="mb-4"
            )
        )
    
    # Return grid layout with scrollable container
    return ft.Div(
        ft.H3("Complete Decklist", cls="text-xl font-bold text-white mb-4"),
        ft.Div(
            ft.Div(
                *card_items,
                cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-3 gap-4"
            ),
            style="max-height: 500px; overflow-y: auto;"  # Make it scrollable
        ),
        cls="mb-8"  # Added extra margin for spacing
    )

def create_decklist_section(leader_id: str, tournament_decklists, card_id2card_data):
    """
    Create a complete decklist section for the leader page.
    
    Args:
        leader_id: Leader card ID
        tournament_decklists: List of tournament decklists
        card_id2card_data: Mapping of card IDs to card data
    
    Returns:
        A Div containing the complete decklist section
    """
    from op_tcg.frontend_fasthtml.utils.decklist import (
        tournament_standings2decklist_data, 
        decklist_data_to_card_ids,
        decklist_data_to_fictive_decklist,
        get_best_matching_decklist
    )
    from op_tcg.frontend_fasthtml.components.decklist_export import create_decklist_export_component
    
    if not tournament_decklists:
        return ft.P("No decklist data available for this leader.", cls="text-red-400")
    
    decklist_data = tournament_standings2decklist_data(tournament_decklists, card_id2card_data)
    common_card_ids = decklist_data_to_card_ids(
        decklist_data,
        occurrence_threshold=0.02,
        exclude_card_ids=[leader_id]
    )
    fictive_decklist = decklist_data_to_fictive_decklist(decklist_data, leader_id)

    return ft.Div(
        ft.Link(rel="stylesheet", href="/public/css/decklist.css", id="decklist-css"),
        ft.Script(src="/public/js/decklist-modal.js", id="decklist-modal-js"),
        ft.P(f"Based on {decklist_data.num_decklists} decklists", cls="text-gray-400 mb-6"),
        display_card_list(decklist_data, common_card_ids),
        
        # Export section with header
        ft.Div(
            ft.H3("Export for OPTCGSim", cls="text-xl font-bold text-white mb-4"),
            create_decklist_export_component(fictive_decklist, leader_id, "leader-page"),
            cls="mb-8"
        ),
        
        # Button to open tournament decklists modal
        ft.Div(
            ft.Button(
                ft.Span("View Tournament Decklists", cls="mr-2"),
                ft.I("→", cls="text-lg"),
                cls="bg-green-600 hover:bg-green-700 text-white font-bold py-3 px-6 rounded-lg transition-colors w-full",
                hx_get="/api/decklist-modal",
                hx_target="body",
                hx_swap="beforeend",
                hx_include="[name='meta_format'],[name='lid'],[name='only_official'],[name='meta_format_region']"
            ),
            cls="mt-6 text-center"
        )
    ) 