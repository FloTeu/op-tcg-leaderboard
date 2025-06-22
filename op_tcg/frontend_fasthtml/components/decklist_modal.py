from fasthtml import ft
from typing import Dict, List
from op_tcg.backend.models.cards import ExtendedCardData, OPTcgLanguage
from op_tcg.frontend_fasthtml.utils.decklist import DecklistData, decklist_to_export_str, ensure_leader_id
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.components.decklist_export import create_decklist_export_component

SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def display_decklist_modal(decklist: dict[str, int], card_id2card_data: dict[str, ExtendedCardData], leader_id: str = None):
    """
    Display a visual representation of a decklist for the modal (without header).
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        card_id2card_data: Mapping of card IDs to card data
        leader_id: Leader card ID to exclude from the display
    
    Returns:
        A Div containing the decklist cards without header
    """
    # Filter out leader card if specified
    filtered_decklist = {k: v for k, v in decklist.items() if k != leader_id} if leader_id else decklist
    
    # Create card items
    card_items = []
    
    # Get the starting index for the complete decklist images
    starting_index = 2000  # Using a different high number for modal to avoid conflicts
    
    # Get all card IDs for the card modal navigation
    all_card_ids = list(filtered_decklist.keys())
    
    for i, (card_id, count) in enumerate(filtered_decklist.items()):
        # Extract set code from card_id
        op_set = card_id.split("-")[0]
        img_url = card_id2card_data[card_id].image_url if card_id in card_id2card_data else f"https://limitlesstcg.nyc3.digitaloceanspaces.com/one-piece/{op_set}/{card_id}_{OPTcgLanguage.EN.upper()}.webp"
        
        card_items.append(
            ft.Div(
                ft.Div(
                    ft.Img(
                        src=img_url, 
                        cls="w-full rounded-lg cursor-pointer hover:opacity-90 transition-opacity",
                        hx_get=f"/api/card-modal?card_id={card_id}&card_elements={'&card_elements='.join(all_card_ids)}&meta_format=latest",
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="cursor-pointer"
                ),
                ft.P(f"x{count}", cls="text-center text-white font-bold text-lg mt-2"),
                cls="mb-4"
            )
        )
    
    # Return grid layout with scrollable container (no header)
    return ft.Div(
        ft.Div(
            *card_items,
            cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-3 lg:grid-cols-3 gap-4"
        ),
        style="max-height: 400px; overflow-y: auto;"  # Make it scrollable
    )

def create_decklist_modal(
    leader_id: str,
    tournament_decklists: list,
    card_id2card_data: dict[str, ExtendedCardData],
    best_matching_decklist: dict[str, int] = None
) -> ft.Div:
    """Create a modal dialog for displaying tournament decklists.
    
    Args:
        leader_id: Leader card ID
        tournament_decklists: List of tournament decklists
        card_id2card_data: Mapping of card IDs to card data
        best_matching_decklist: Best matching tournament decklist
        
    Returns:
        A FastHTML Div containing the modal dialog
    """
    
    # Sort tournament decklists by placing (None placings at the end)
    tournament_decklists.sort(key=lambda x: (x.placing is None, x.placing))
    
    # Create tournament decklist dropdown options with enhanced information
    decklist_options = []
    for td_obj in tournament_decklists:
        if not td_obj.tournament_id or not td_obj.player_id:
            continue  # Skip if we don't have both IDs
            
        option_text = []
        if td_obj.player_id:
            option_text.append(f"Player: {td_obj.player_id}")
        if td_obj.tournament_id:
            option_text.append(f"Tournament: {td_obj.tournament_id[:25]}{'...' if len(td_obj.tournament_id) > 25 else ''}")
        if td_obj.placing:
            option_text.append(f"Rank: #{td_obj.placing}")
        if hasattr(td_obj, 'date') and td_obj.date:
            option_text.append(f"Date: {td_obj.date}")
            
        # Create a composite value using both IDs
        value = f"{td_obj.tournament_id}:{td_obj.player_id}"
        # Use the joined text directly as the option text
        option_display_text = " | ".join(option_text)
        decklist_options.append((option_display_text, value))
    
    # Find the best matching decklist in the tournament_decklists for pre-selection
    best_matching_td = next(
        (td for td in tournament_decklists if td.decklist == best_matching_decklist),
        None
    ) if best_matching_decklist else None
    
    # Create tournament decklist select component with enhanced styling
    tournament_decklist_select_component = ft.Div()  # Default to empty div
    if decklist_options:
        # Set the selected value if we have a best matching decklist
        selected_value = None
        if best_matching_td and best_matching_td.tournament_id and best_matching_td.player_id:
            selected_value = f"{best_matching_td.tournament_id}:{best_matching_td.player_id}"
        
        tournament_decklist_select_component = ft.Div(
            ft.Label("Select Tournament Decklist:", cls="text-white font-medium block mb-3"),
            ft.Select(
                *[
                    ft.Option(
                        text,
                        value=value,
                        selected=(value == selected_value)
                    ) for text, value in decklist_options
                ],
                id="tournament-decklist-select-modal",
                cls=SELECT_CLS + " styled-select mb-4",
                hx_get="/api/decklist/tournament-decklist-modal",
                hx_target="#selected-tournament-decklist-content-modal",
                hx_include="[name='lid'], [name='meta_format']",
                hx_trigger="change",
                hx_swap="innerHTML",
                hx_vals='''js:{
                    "tournament_id": event.target.value.split(":")[0],
                    "player_id": event.target.value.split(":")[1]
                }''',
                hx_indicator="#tournament-decklist-loading"
            ),
            # Add loading indicator
            create_loading_spinner(
                id="tournament-decklist-loading",
                size="w-6 h-6",
                container_classes="min-h-[40px] hidden"
            ),
            cls="mb-6"
        )
    
    # Create tournament stats if available
    tournament_stats = ft.Div()
    if tournament_decklists:
        total_tournaments = len(set(td.tournament_id for td in tournament_decklists))
        total_players = len(tournament_decklists)
        top_8_count = len([td for td in tournament_decklists if td.placing and td.placing <= 8])
        wins = len([td for td in tournament_decklists if td.placing and td.placing == 1])
        
        tournament_stats = ft.Div(
            ft.H3("Tournament Performance", cls="text-xl font-bold text-white mb-4"),
            ft.Div(
                ft.Div(
                    ft.Div(str(total_tournaments), cls="text-2xl font-bold text-blue-400"),
                    ft.Div("Tournaments", cls="text-gray-300 text-sm"),
                    cls="text-center"
                ),
                ft.Div(
                    ft.Div(str(total_players), cls="text-2xl font-bold text-green-400"),
                    ft.Div("Decklists", cls="text-gray-300 text-sm"),
                    cls="text-center"
                ),
                ft.Div(
                    ft.Div(str(top_8_count), cls="text-2xl font-bold text-yellow-400"),
                    ft.Div("Top 8", cls="text-gray-300 text-sm"),
                    cls="text-center"
                ),
                ft.Div(
                    ft.Div(str(wins), cls="text-2xl font-bold text-purple-400"),
                    ft.Div("Wins", cls="text-gray-300 text-sm"),
                    cls="text-center"
                ),
                cls="grid grid-cols-4 gap-4 mb-6"
            ),
            cls="bg-gray-750 rounded-lg p-4 mb-6"
        )
    
    # Initial decklist content with export functionality
    initial_decklist_content = ft.Div()
    if best_matching_decklist:
        initial_decklist_content = ft.Div(
            create_decklist_export_component(best_matching_decklist, leader_id, "initial"),
            display_decklist_modal(best_matching_decklist, card_id2card_data, leader_id)
        )
    else:
        initial_decklist_content = ft.Div(
            ft.P("Select a tournament decklist from the dropdown above to view details.", cls="text-gray-400 text-center p-8"),
            ft.I("📋", cls="text-4xl text-gray-500 block text-center mb-2"),
            cls="bg-gray-750 rounded-lg"
        )
    
    return ft.Div(
        # Modal backdrop
        ft.Div(
            # Modal content container
            ft.Div(
                # Close button
                ft.Button(
                    ft.I("×", cls="text-3xl leading-none"),
                    cls="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors z-10 w-8 h-8 flex items-center justify-center",
                    onclick="event.stopPropagation(); document.getElementById('decklist-modal-backdrop').remove();"
                ),
                
                # Modal header
                ft.Div(
                    ft.H2(
                        ft.Span("Tournament Decklists", cls="text-3xl font-bold text-white"),
                        ft.Span(f" ({leader_id})", cls="text-gray-400 text-xl ml-2"),
                        cls="mb-2"
                    ),
                    ft.P(f"Explore {len(tournament_decklists)} tournament decklists from competitive play", cls="text-gray-400 mb-6"),
                    cls="border-b border-gray-700 pb-6 mb-6"
                ),
                
                # Enhanced tournament content
                ft.Div(
                    # Tournament statistics
                    tournament_stats,
                    
                    # Tournament decklist selector
                    tournament_decklist_select_component,
                    
                    # Selected decklist display (single header)
                    ft.Div(
                        ft.H3("Selected Tournament Decklist", cls="text-xl font-bold text-white mb-4"),
                        ft.Div(
                            initial_decklist_content,
                            id="selected-tournament-decklist-content-modal",
                            cls="min-h-[400px]"
                        ),
                        cls="bg-gray-800 rounded-lg p-4"
                    ) if tournament_decklists else ft.Div(
                        ft.P("No tournament decklists available for this leader.", cls="text-gray-400 text-center p-8"),
                        cls="bg-gray-750 rounded-lg"
                    ),
                    
                    cls="max-h-[70vh] overflow-y-auto"
                ),
                
                cls="bg-gray-800 rounded-lg p-6 max-w-5xl w-full mx-4 relative max-h-[90vh] overflow-hidden",
                onclick="event.stopPropagation()"  # Prevent clicks inside modal from closing it
            ),
            cls="decklist-modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center overflow-y-auto py-4",
            onclick="if (event.target === this) { event.target.remove(); }",
            id="decklist-modal-backdrop"  # Add ID for specific targeting
        ),
        
        # Include required CSS and JS
        ft.Link(rel="stylesheet", href="/public/css/decklist.css", id="decklist-css-modal"),
        ft.Script(src="/public/js/decklist-modal.js", id="decklist-modal-js-modal"),
        
        # Enhanced modal styles with proper z-index management
        ft.Style("""
            .decklist-modal-backdrop {
                z-index: 9999 !important;
                backdrop-filter: blur(4px);
            }
            .carousel-item {
                display: none;
            }
            .carousel-item.active {
                display: block;
            }
            .bg-gray-750 {
                background-color: #374151;
            }
            #tournament-decklist-loading.htmx-request {
                display: block !important;
            }
            /* Ensure card modals appear on top of decklist modal */
            .modal-backdrop:not(.decklist-modal-backdrop) {
                z-index: 10000 !important;
            }
            /* Override any sidebar z-index */
            .decklist-modal-backdrop {
                z-index: 9999 !important;
            }
        """),
        
        # JavaScript to prevent card modal from closing decklist modal
        ft.Script("""
            document.addEventListener('htmx:beforeSwap', function(evt) {
                // If a card modal is being closed, don't affect the decklist modal
                if (evt.target.classList && evt.target.classList.contains('modal-backdrop') && 
                    !evt.target.classList.contains('decklist-modal-backdrop')) {
                    evt.preventDefault();
                    evt.target.remove();
                }
            });
            
            // Handle card modal close buttons specifically
            document.addEventListener('click', function(evt) {
                if (evt.target.closest('.modal-backdrop:not(.decklist-modal-backdrop)')) {
                    const cardModal = evt.target.closest('.modal-backdrop:not(.decklist-modal-backdrop)');
                    if (cardModal && evt.target === cardModal) {
                        cardModal.remove();
                        evt.stopPropagation();
                    }
                }
            });
        """)
    ) 