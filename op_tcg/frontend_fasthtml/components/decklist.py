from fasthtml import ft
from op_tcg.backend.models.cards import OPTcgLanguage, LatestCardPrice
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

def display_decklist(decklist: dict[str, int], leader_id: str = None):
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
        img_url = f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
        
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

def display_decklist_export(decklist: dict[str, int], leader_id: str):
    """
    Display an exportable decklist with copy functionality.
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        leader_id: Leader card ID
    
    Returns:
        A Div containing the exportable decklist
    """
    # Ensure leader is included in the decklist
    complete_decklist = ensure_leader_id(decklist, leader_id)
    export_str = decklist_to_export_str(complete_decklist)
    
    clipboard_script = """
    document.addEventListener('DOMContentLoaded', function() {
        var copyBtn = document.getElementById('decklist-copy-btn');
        if (!copyBtn) return;
        
        copyBtn.addEventListener('click', function() {
            const decklistText = document.getElementById('decklist-export').textContent;
            
            navigator.clipboard.writeText(decklistText).then(() => {
                const originalText = copyBtn.textContent;
                copyBtn.textContent = 'Copied!';
                copyBtn.disabled = true;
                
                setTimeout(() => {
                    copyBtn.textContent = originalText;
                    copyBtn.disabled = false;
                }, 2000);
            }).catch(err => {
                console.error('Failed to copy: ', err);
            });
        });
    });
    """
    
    return ft.Div(
        # Header
        ft.H3("Export for OPTCGSim", cls="text-xl font-bold text-white mb-4"),
        
        # Container for export content and button
        ft.Div(
            # Export text area
            ft.Pre(
                export_str,
                id="decklist-export",
                cls="bg-gray-900 text-white p-4 rounded-lg font-mono text-sm overflow-auto mb-4"
            ),
            
            # Copy button
            ft.Button(
                "Copy to Clipboard",
                id="decklist-copy-btn",
                cls="bg-blue-600 hover:bg-blue-700 text-white font-bold py-2 px-4 rounded"
            ),
            
            # JavaScript for clipboard functionality 
            ft.Script(clipboard_script),
            
            cls="bg-gray-800 p-4 rounded-lg"
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
    
    if not tournament_decklists:
        return ft.P("No decklist data available for this leader.", cls="text-red-400")
    
    decklist_data = tournament_standings2decklist_data(tournament_decklists, card_id2card_data)
    common_card_ids = decklist_data_to_card_ids(
        decklist_data,
        occurrence_threshold=0.02,
        exclude_card_ids=[leader_id]
    )
    fictive_decklist = decklist_data_to_fictive_decklist(decklist_data, leader_id)
    best_matching_decklist_dict = get_best_matching_decklist(tournament_decklists, decklist_data)
    
    # Sort tournament decklists by placing (None placings at the end)
    tournament_decklists.sort(key=lambda x: (x.placing is None, x.placing))
    
    decklist_options = []
    for td_obj in tournament_decklists:
        if not td_obj.tournament_id or not td_obj.player_id:
            continue  # Skip if we don't have both IDs
            
        option_text = []
        if td_obj.player_id:
            option_text.append(f"Player: {td_obj.player_id}")
        if td_obj.tournament_id:
            option_text.append(f"Tournament: {td_obj.tournament_id[:20]}{'...' if len(td_obj.tournament_id) > 20 else ''}")
        if td_obj.placing:
            option_text.append(f"#{td_obj.placing}")
            
        # Create a composite value using both IDs
        value = f"{td_obj.tournament_id}:{td_obj.player_id}"
        
        decklist_options.append(ft.Option(" - ".join(option_text), value=value))

    tournament_decklist_select_component = ft.Div()  # Default to empty div
    if decklist_options:
        tournament_decklist_select_component = ft.Div(
            ft.Label("Select Tournament Decklist:", cls="text-white font-medium block mb-2"),
            ft.Select(
                *decklist_options,
                id="tournament-decklist-select",
                cls=SELECT_CLS + " styled-select mb-2",
                hx_get="/api/decklist/tournament-decklist",
                hx_target="#selected-tournament-decklist-content",
                hx_include="[name='lid'], [name='meta_format']",
                hx_trigger="change",
                hx_swap="innerHTML",
                hx_vals='''{"tournament_id": "this.value.split(':')[0]", "player_id": "this.value.split(':')[1]"}''',
            ),
            cls="mb-4"
        )
    
    # Find the best matching decklist in the tournament_decklists
    best_matching_td = next(
        (td for td in tournament_decklists if td.decklist == best_matching_decklist_dict),
        None
    ) if best_matching_decklist_dict else None
    
    # If we found the best matching tournament decklist, pre-select it in the dropdown
    if best_matching_td and best_matching_td.tournament_id and best_matching_td.player_id:
        # Update the select's value to match the best decklist
        tournament_decklist_select_component.children[1].value = f"{best_matching_td.tournament_id}:{best_matching_td.player_id}"
    
    initial_decklist_content = display_decklist(best_matching_decklist_dict, leader_id) if best_matching_decklist_dict else ft.P("Select a decklist from the dropdown to view details.", cls="text-white p-4")

    return ft.Div(
        ft.Link(rel="stylesheet", href="/static/css/decklist.css", id="decklist-css"),
        ft.Script(src="/static/js/decklist-modal.js", id="decklist-modal-js"),
        ft.P(f"Based on {decklist_data.num_decklists} decklists", cls="text-gray-400 mb-6"),
        display_card_list(decklist_data, common_card_ids),
        display_decklist_export(fictive_decklist, leader_id),
        
        ft.Div(
            tournament_decklist_select_component,
            
            ft.Details(
                ft.Summary("View Tournament Decklist", cls="text-lg font-semibold text-white cursor-pointer hover:text-blue-400"),
                ft.Div(
                    initial_decklist_content,
                    id="selected-tournament-decklist-content"
                ),
                open=(True if best_matching_decklist_dict else False),
                cls="mb-6 bg-gray-750 p-3 rounded-lg shadow"
            ) if tournament_decklists else ft.Div(),
            
            cls="space-y-6"
        )
    ) 