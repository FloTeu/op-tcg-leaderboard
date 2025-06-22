from fasthtml import ft
from typing import Dict, List
from op_tcg.backend.models.cards import ExtendedCardData, OPTcgLanguage, CardCurrency
from op_tcg.frontend_fasthtml.utils.decklist import DecklistData, decklist_to_export_str, ensure_leader_id
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.components.decklist_export import create_decklist_export_component

SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def display_decklist_modal(decklist: dict[str, int], card_id2card_data: dict[str, ExtendedCardData], leader_id: str = None, currency: CardCurrency = CardCurrency.EURO):
    """
    Display a visual representation of a decklist for the modal (without header).
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        card_id2card_data: Mapping of card IDs to card data
        leader_id: Leader card ID to exclude from the display
        currency: Selected currency for price display
    
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
        
        # Get price information based on selected currency
        card_data = card_id2card_data.get(card_id)
        price_info = ""
        price_class = "text-center text-gray-300 text-xs mt-1"
        
        if card_data and hasattr(card_data, 'latest_eur_price') and hasattr(card_data, 'latest_usd_price'):
            if currency == CardCurrency.EURO and card_data.latest_eur_price:
                price_info = f"€{card_data.latest_eur_price:.2f}"
                price_class = "text-center text-green-400 text-xs mt-1 font-medium"
            elif currency == CardCurrency.US_DOLLAR and card_data.latest_usd_price:
                price_info = f"${card_data.latest_usd_price:.2f}"
                price_class = "text-center text-blue-400 text-xs mt-1 font-medium"
            elif card_data.latest_eur_price and card_data.latest_usd_price:
                # Fallback to EUR if selected currency not available
                price_info = f"€{card_data.latest_eur_price:.2f}"
                price_class = "text-center text-green-400 text-xs mt-1 font-medium"
            elif card_data.latest_eur_price:
                price_info = f"€{card_data.latest_eur_price:.2f}"
                price_class = "text-center text-green-400 text-xs mt-1 font-medium"
            elif card_data.latest_usd_price:
                price_info = f"${card_data.latest_usd_price:.2f}"
                price_class = "text-center text-blue-400 text-xs mt-1 font-medium"
        
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
                    cls="cursor-pointer relative"
                ),
                ft.Div(
                    ft.P(f"x{count}", cls="text-center text-white font-bold text-sm bg-gray-900 bg-opacity-80 rounded px-2 py-1"),
                    ft.P(price_info, cls=price_class) if price_info else ft.P("N/A", cls="text-center text-gray-500 text-xs mt-1"),
                    cls="mt-1"
                ),
                cls="mb-2 bg-gray-750 rounded-lg p-2 hover:bg-gray-700 transition-colors"
            )
        )
    
    # Return grid layout with increased height and smaller cards
    return ft.Div(
        ft.Div(
            *card_items,
            cls="grid grid-cols-4 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-7 gap-3"
        ),
        style="max-height: 600px; overflow-y: auto;"  # Increased height
    )

def create_decklist_modal(
    leader_id: str,
    tournament_decklists: list,
    card_id2card_data: dict[str, ExtendedCardData]
) -> ft.Div:
    """Create a modal dialog for displaying tournament decklists.
    
    Args:
        leader_id: Leader card ID
        tournament_decklists: List of tournament decklists
        card_id2card_data: Mapping of card IDs to card data
        
    Returns:
        A FastHTML Div containing the modal dialog
    """
    
    # Sort tournament decklists by placing (None placings at the end, then by placing ascending)
    tournament_decklists.sort(key=lambda x: (x.placing is None, x.placing or float('inf')))
    
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
    
    
    # use best ranked
    selected_td = tournament_decklists[0] if tournament_decklists else None
    
    # Create tournament decklist select component with enhanced styling
    tournament_decklist_select_component = ft.Div()  # Default to empty div
    if decklist_options:
        # Set the selected value - prefer best ranked (first in list)
        selected_value = None
        if selected_td and selected_td.tournament_id and selected_td.player_id:
            selected_value = f"{selected_td.tournament_id}:{selected_td.player_id}"
        
        tournament_decklist_select_component = ft.Div(
            # Row with tournament decklist and currency selection
            ft.Div(
                # Tournament decklist selector (left side)
                ft.Div(
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
                        cls=SELECT_CLS + " styled-select",
                        hx_get="/api/decklist/tournament-decklist-modal",
                        hx_target="#selected-tournament-decklist-content-modal",
                        hx_include="[name='lid'], [name='meta_format'], #currency-select-modal",
                        hx_trigger="change",
                        hx_swap="innerHTML",
                        hx_vals='''js:{
                            "tournament_id": event.target.value.split(":")[0],
                            "player_id": event.target.value.split(":")[1]
                        }''',
                        hx_indicator="#tournament-decklist-loading"
                    ),
                    cls="flex-1"
                ),
                
                # Currency selector (right side)
                ft.Div(
                    ft.Label("Currency:", cls="text-white font-medium block mb-3"),
                    ft.Select(
                        ft.Option("EUR (€)", value="EURO", selected=True),
                        ft.Option("USD ($)", value="US_DOLLAR"),
                        id="currency-select-modal",
                        name="currency",
                        cls=SELECT_CLS + " styled-select",
                        hx_get="/api/decklist/tournament-decklist-modal",
                        hx_target="#selected-tournament-decklist-content-modal",
                        hx_include="[name='lid'], [name='meta_format'], #tournament-decklist-select-modal",
                        hx_trigger="change",
                        hx_swap="innerHTML",
                        hx_vals='''js:{
                            "tournament_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[0],
                            "player_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[1]
                        }''',
                        hx_indicator="#tournament-decklist-loading"
                    ),
                    cls="w-32 ml-4"
                ),
                cls="flex items-end gap-4 mb-4"
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
    
    # Initial decklist content with export functionality - use best ranked decklist
    initial_decklist_content = ft.Div()
    
    if selected_td.decklist:
        initial_decklist_content = ft.Div(
            create_decklist_export_component(selected_td.decklist, leader_id, "initial"),
            display_decklist_modal(selected_td.decklist, card_id2card_data, leader_id, CardCurrency.EURO)
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
                    cls="absolute top-6 right-6 text-gray-400 hover:text-white transition-colors z-20 w-8 h-8 flex items-center justify-center",
                    onclick="event.stopPropagation(); document.getElementById('decklist-modal-backdrop').remove();"
                ),
                
                # Modal header - fixed at top with proper spacing
                ft.Div(
                    ft.H2(
                        ft.Span("Tournament Decklists", cls="text-3xl font-bold text-white"),
                        ft.Span(f" ({leader_id})", cls="text-gray-400 text-xl ml-2"),
                        cls="mb-2 pr-16 pt-6"  # Increased right padding and top padding
                    ),
                    ft.P(f"Explore {len(tournament_decklists)} tournament decklists from competitive play", cls="text-gray-400 mb-6"),
                    cls="border-b border-gray-700 pb-6 mb-6 relative bg-gray-800"  # Added background to ensure visibility
                ),
                
                # Scrollable content area
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
                    
                    cls="max-h-[60vh] overflow-y-auto px-6"  # Added horizontal padding and reduced height
                ),
                
                cls="bg-gray-800 rounded-lg max-w-6xl w-full mx-4 relative max-h-[90vh] overflow-hidden mt-4",  # Removed padding, reduced top margin
                onclick="event.stopPropagation()"  # Prevent clicks inside modal from closing it
            ),
            cls="decklist-modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center overflow-y-auto py-4",  # Reduced vertical padding
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