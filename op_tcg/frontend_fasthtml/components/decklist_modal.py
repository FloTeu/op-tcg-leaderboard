from fasthtml import ft
from op_tcg.backend.etl.extract import get_card_image_url
from op_tcg.backend.models.cards import ExtendedCardData, OPTcgLanguage
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner
from op_tcg.frontend_fasthtml.components.decklist_export import create_decklist_export_component

SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def display_decklist_modal(decklist: dict[str, int], card_id2card_data: dict[str, ExtendedCardData], leader_id: str = None, currency: str = "EUR"):
    """
    Display a visual representation of a decklist for the modal (without header).
    
    Args:
        decklist: Dictionary mapping card IDs to counts
        card_id2card_data: Mapping of card IDs to card data
        leader_id: Leader card ID to exclude from the display
        currency: Currency to display prices in ("EUR" or "USD")
    
    Returns:
        A Div containing the decklist cards without header
    """
    # Filter out leader card if specified
    filtered_decklist = {k: v for k, v in decklist.items() if k != leader_id} if leader_id else decklist
    
    # Create card items
    card_items = []
    
    # Get all card IDs for the card modal navigation
    all_card_ids = list(filtered_decklist.keys())
    
    for i, (card_id, count) in enumerate(filtered_decklist.items()):
        img_url = card_id2card_data[card_id].image_url if card_id in card_id2card_data else get_card_image_url(card_id, OPTcgLanguage.JP)
        
        # Get price information based on selected currency
        card_data = card_id2card_data.get(card_id)
        price_info = ""
        price_value = 0
        if card_data and hasattr(card_data, 'latest_eur_price') and hasattr(card_data, 'latest_usd_price'):
            if currency == "EUR" and card_data.latest_eur_price:
                price_value = card_data.latest_eur_price
                price_info = f"€{card_data.latest_eur_price:.2f}"
            elif currency == "USD" and card_data.latest_usd_price:
                price_value = card_data.latest_usd_price
                price_info = f"${card_data.latest_usd_price:.2f}"
        
        # Determine if card is expensive (over 5 EUR/USD)
        is_expensive = price_value > 5.0
        price_classes = "text-gray-300 text-xs"
        if is_expensive:
            price_classes = "text-red-300 text-xs font-bold"
            if price_value > 20.0:  # Very expensive
                price_classes = "text-red-400 text-xs font-bold bg-red-900/30 px-1 py-0.5 rounded"
        
        card_items.append(
            ft.Div(
                ft.Div(
                    ft.Img(
                        src=img_url, 
                        cls="w-full rounded-lg cursor-pointer hover:opacity-90 transition-opacity",
                        hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest",
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="cursor-pointer"
                ),
                ft.Div(
                    ft.Div(
                        ft.Span(f"x{count}", cls="text-white font-bold text-sm"),
                        ft.Span(
                            f"💰 {price_info}" if is_expensive else price_info, 
                            cls=price_classes
                        ) if price_info else ft.Span("", cls="text-xs"),
                        cls="flex justify-between items-center w-full"
                    ),
                    cls="mt-1 px-1"
                ),
                cls="mb-2"
            )
        )
    
    # Return grid layout with increased height and smaller cards
    return ft.Div(
        ft.Div(
            *card_items,
            cls="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-2"
        ),
        style="max-height: 600px; overflow-y: auto;"  # Increased height
    )

def create_decklist_modal(
    leader_id: str,
    tournament_decklists: list,
    card_id2card_data: dict[str, ExtendedCardData],
    selected_tournament_id: str | None = None,
    selected_player_id: str | None = None,
    selected_currency: str = "EUR",
    days: str | None = None,
    placing: str | None = None
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
    
    
    # use deep-linked selection if provided; otherwise best ranked
    selected_td = tournament_decklists[0] if tournament_decklists else None
    if selected_tournament_id and selected_player_id:
        for td in tournament_decklists:
            if td.tournament_id == selected_tournament_id and td.player_id == selected_player_id:
                selected_td = td
                break
    
    # Create tournament decklist select component with enhanced styling
    tournament_decklist_select_component = ft.Div()  # Default to empty div
    if decklist_options:
        # Set the selected value - prefer best ranked (first in list)
        selected_value = None
        if selected_td and selected_td.tournament_id and selected_td.player_id:
            selected_value = f"{selected_td.tournament_id}:{selected_td.player_id}"
        
        # Create hidden inputs for preserving filter parameters
        hidden_inputs = [ft.Input(type="hidden", name="lid", value=leader_id)]
        if days is not None:
            hidden_inputs.append(ft.Input(type="hidden", name="days", value=days))
        if placing is not None:
            hidden_inputs.append(ft.Input(type="hidden", name="placing", value=placing))
        
        tournament_decklist_select_component = ft.Div(
            *hidden_inputs,
            ft.Div(
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
                        cls=SELECT_CLS + " styled-select mb-4",
                        hx_get="/api/decklist/tournament-decklist-modal",
                        hx_target="#selected-tournament-decklist-content-modal",
                        hx_include="[name='lid'], [name='meta_format'], [name='days'], [name='placing'], #currency-select-modal",
                        hx_trigger="change",
                        hx_swap="innerHTML",
                        hx_vals='''js:{
                            "tournament_id": event.target.value.split(":")[0],
                            "player_id": event.target.value.split(":")[1]
                        }''',
                        hx_indicator="#tournament-decklist-loading",
                        onchange='(function(){try{const p=new URLSearchParams(window.location.search);const v=document.getElementById("tournament-decklist-select-modal").value.split(":");p.set("tournament_id",v[0]);p.set("player_id",v[1]);const c=document.getElementById("currency-select-modal");if(c&&c.value){p.set("currency",c.value)}p.set("modal","decklist");const u=window.location.pathname+"?"+p.toString();window.history.replaceState({},"",u);}catch(e){}})()'
                    ),
                    cls="flex-1"
                ),
                ft.Div(
                    ft.Label("Currency:", cls="text-white font-medium block mb-3"),
                    ft.Select(
                        ft.Option("EUR (€)", value="EUR", selected=(selected_currency == "EUR")),
                        ft.Option("USD ($)", value="USD", selected=(selected_currency == "USD")),
                        id="currency-select-modal",
                        name="currency",
                        cls=SELECT_CLS + " styled-select mb-4",
                        hx_get="/api/decklist/tournament-decklist-modal",
                        hx_target="#selected-tournament-decklist-content-modal",
                        hx_include="#tournament-decklist-select-modal, [name='lid'], [name='meta_format'], [name='days'], [name='placing']",
                        hx_trigger="change",
                        hx_swap="innerHTML",
                        hx_vals='''js:{
                            "tournament_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[0],
                            "player_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[1]
                        }''',
                        hx_indicator="#tournament-decklist-loading",
                        onchange='(function(){try{const p=new URLSearchParams(window.location.search);const v=document.getElementById("tournament-decklist-select-modal").value.split(":");p.set("tournament_id",v[0]);p.set("player_id",v[1]);const c=document.getElementById("currency-select-modal");if(c&&c.value){p.set("currency",c.value)}p.set("modal","decklist");const u=window.location.pathname+"?"+p.toString();window.history.replaceState({},"",u);}catch(e){}})()'
                    ),
                    cls="flex-none w-full sm:w-40 sm:ml-4 mt-0"
                ),
                cls="flex flex-col sm:flex-row sm:items-end gap-4"
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
                cls="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-6"
            ),
            cls="bg-gray-750 rounded-lg p-4 mb-6"
        )
    
    # Initial decklist content with export functionality - use best ranked decklist
    initial_decklist_content = ft.Div()
    
    if selected_td and selected_td.decklist:
        initial_decklist_content = ft.Div(
            display_decklist_modal(selected_td.decklist, card_id2card_data, leader_id, selected_currency or "EUR"),
            create_decklist_export_component(selected_td.decklist, leader_id, "initial")
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
                # Close button + Share
                ft.Div(
                    ft.Button(
                        ft.Span(
                            ft.Span("🔗", cls="text-base"),
                            ft.Span("Copy link", cls="hidden sm:inline"),
                            cls="inline-flex items-center gap-2"
                        ),
                        type="button",
                        title="Copy shareable link",
                        cls="ml-2 inline-flex items-center gap-2 rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 px-4 py-2 text-white font-semibold shadow-sm hover:from-blue-600 hover:to-indigo-700 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-400 active:translate-y-px transition",
                        onclick='(function(evt){evt.preventDefault();var btn=evt.currentTarget; (async function(){ try{function buildShareURL(){const p=new URLSearchParams(window.location.search);const lidInput=document.querySelector("[name=lid]");if(lidInput&&lidInput.value){p.set("lid",lidInput.value);}const daysInput=document.querySelector("[name=days]");if(daysInput&&daysInput.value){p.set("days",daysInput.value);}const placingInput=document.querySelector("[name=placing]");if(placingInput&&placingInput.value){p.set("placing",placingInput.value);}const sel=document.getElementById("tournament-decklist-select-modal");if(sel&&sel.value){const v=sel.value.split(":");p.set("tournament_id",v[0]);p.set("player_id",v[1]);}const c=document.getElementById("currency-select-modal");if(c&&c.value){p.set("currency",c.value)}p.set("modal","decklist");return window.location.origin+window.location.pathname+"?"+p.toString();}const url=buildShareURL(); try{ if(navigator.clipboard&&navigator.clipboard.writeText){ await navigator.clipboard.writeText(url); } else { throw new Error("no-async-clipboard"); } } catch(e){ var ta=document.createElement("textarea"); ta.value=url; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta); } if(!btn) return; var orig=btn.getAttribute("data-orig-html"); if(!orig){orig=btn.innerHTML; btn.setAttribute("data-orig-html", orig);} btn.innerHTML = "<span class=\"inline-flex items-center gap-2\">✅ <span class=\"hidden sm:inline\">Copied!</span></span>"; btn.classList.add("ring-2","ring-green-400"); setTimeout(function(){btn.innerHTML=orig; btn.classList.remove("ring-2","ring-green-400");}, 1500); } catch(e){} })(); })(event)'
                    ),
                    ft.Button(
                        ft.Span("×", cls="text-lg"),
                        type="button",
                        cls="inline-flex items-center justify-center w-9 h-9 rounded-full bg-gray-700/60 hover:bg-gray-700 text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-400 transition",
                        onclick='event.stopPropagation();(function(){try{const p=new URLSearchParams(window.location.search);p.delete("tournament_id");p.delete("player_id");p.delete("currency");p.delete("modal");const u=window.location.pathname+(p.toString()?"?"+p.toString():"");window.history.replaceState({},"",u);}catch(e){};var el=document.getElementById("decklist-modal-backdrop");if(el)el.remove();})()'
                    ),
                    cls="absolute top-4 right-4 flex items-center"
                ),
                
                # Modal header with leader image - NOT in scrollable area
                ft.Div(
                    # Leader card image section
                    ft.Div(
                        ft.A(
                            ft.Img(
                                src=card_id2card_data[leader_id].image_url if leader_id in card_id2card_data else get_card_image_url(leader_id, OPTcgLanguage.EN),
                                alt=f"{leader_id} card",
                                cls="w-full h-full object-cover rounded-lg shadow-2xl ring-2 transition-all duration-300",
                                style="max-width: 180px; max-height: 250px; --tw-ring-color: rgb(250 204 21 / 0.5); --tw-ring-offset-shadow: 0 0 0 0 transparent; --tw-ring-shadow: 0 0 0 2px var(--tw-ring-color);",
                            ),
                            href="#",
                            title="View leader details page",
                            cls="block leader-link-to-page",
                            data_leader_id=leader_id,
                            onclick=f"""event.preventDefault(); 
                                const params = new URLSearchParams(window.location.search); 
                                params.set('lid', '{leader_id}'); 
                                params.delete('tournament_id'); 
                                params.delete('player_id'); 
                                params.delete('currency'); 
                                params.delete('modal'); 
                                window.location.href = '/leader?' + params.toString();"""
                        ),
                        cls="decklist-modal-leader-card flex-shrink-0 mb-4 sm:mb-0 sm:mr-6"
                    ),
                    # Header text section
                    ft.Div(
                        ft.H2(
                            ft.Span("Tournament Decklists", cls="text-3xl font-bold text-white"),
                            cls="mb-2 pr-16"
                        ),
                        ft.Div(
                            ft.Span(
                                leader_id,
                                cls="inline-flex items-center px-3 py-1 rounded-full text-sm font-semibold bg-gradient-to-r from-yellow-500/20 to-orange-500/20 text-yellow-300 border border-yellow-500/30"
                            ),
                            cls="mb-3"
                        ),
                        ft.P(
                            f"Explore {len(tournament_decklists)} tournament decklists from competitive play",
                            cls="text-gray-400"
                        ),
                        cls="flex-1 flex flex-col justify-center"
                    ),
                    cls="flex flex-col sm:flex-row items-center sm:items-start mb-6 pb-6 border-b border-gray-700"
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
                    
                    cls="max-h-[60vh] overflow-y-auto"
                ),
                
                cls="bg-gray-800 rounded-lg p-4 sm:p-6 max-w-sm sm:max-w-lg md:max-w-2xl lg:max-w-4xl xl:max-w-6xl w-full mx-2 sm:mx-4 relative",
                onclick="event.stopPropagation()"  # Prevent clicks inside modal from closing it
            ),
            cls="decklist-modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-start justify-center overflow-y-auto py-4",
            onclick='if (event.target === this) { (function(){try{const p=new URLSearchParams(window.location.search);p.delete("tournament_id");p.delete("player_id");p.delete("currency");p.delete("modal");const u=window.location.pathname+(p.toString()?"?"+p.toString():"");window.history.replaceState({},"",u);}catch(e){};var el=document.getElementById("decklist-modal-backdrop");if(el)el.remove();})() }',
            id="decklist-modal-backdrop"  # Add ID for specific targeting
        ),
        
        # Include required CSS and JS
        ft.Script(src="/public/js/decklist-modal.js", id="decklist-modal-js-modal"),
        
        # Enhanced modal styles with proper z-index management and mobile overflow prevention
        ft.Style("""
            .decklist-modal-backdrop {
                z-index: 9999 !important;
                backdrop-filter: blur(4px);
                overflow-x: hidden !important;
                overflow-y: auto !important;
                max-width: 100vw !important;
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
            /* Prevent horizontal overflow on mobile when modal is open */
            body:has(.decklist-modal-backdrop) {
                overflow-x: hidden !important;
                max-width: 100vw !important;
            }
            /* Ensure modal content stays within viewport on mobile */
            @media (max-width: 640px) {
                .decklist-modal-backdrop > div {
                    max-width: 100vw !important;
                    margin: 0 !important;
                    box-sizing: border-box !important;
                }
            }
        """),
        
        # JavaScript: attach robust click handler for Share after insertion and prevent card modal closing decklist modal
        ft.Script("""
            (function(){
                function attachDecklistShareHandler(){
                    var btn = document.querySelector('#decklist-modal-backdrop button[title="Copy shareable link"]');
                    if (!btn || btn.dataset.bound === '1') return;
                    btn.dataset.bound = '1';
                    btn.addEventListener('click', async function(evt){
                        evt.preventDefault();
                        try{
                            // Use unified share URL building function
                            function buildShareURL() {{
                                const p = new URLSearchParams(window.location.search);
                                
                                // Get leader ID from hidden input (for tournament page context)
                                const lidInput = document.querySelector('[name="lid"]');
                                if (lidInput && lidInput.value) {{
                                    p.set('lid', lidInput.value);
                                }}
                                
                                // Get tournament filter parameters from hidden inputs
                                const daysInput = document.querySelector('[name="days"]');
                                if (daysInput && daysInput.value) {{
                                    p.set('days', daysInput.value);
                                }}
                                
                                const placingInput = document.querySelector('[name="placing"]');
                                if (placingInput && placingInput.value) {{
                                    p.set('placing', placingInput.value);
                                }}
                                
                                // Always try to get selected decklist if available
                                const sel = document.getElementById('tournament-decklist-select-modal');
                                if (sel && sel.value) {{
                                    const v = sel.value.split(':');
                                    p.set('tournament_id', v[0]);
                                    p.set('player_id', v[1]);
                                }}
                                
                                // Currency selection
                                const c = document.getElementById('currency-select-modal');
                                if (c && c.value) {{ p.set('currency', c.value); }}
                                
                                // Always set modal parameter
                                p.set('modal', 'decklist');
                                
                                return window.location.origin + window.location.pathname + '?' + p.toString();
                            }}
                            
                            const url = buildShareURL();
                            if (!url) return;
                            try { await navigator.clipboard.writeText(url); }
                            catch(e){
                                const ta = document.createElement('textarea');
                                ta.value = url; document.body.appendChild(ta); ta.select(); document.execCommand('copy'); document.body.removeChild(ta);
                            }
                            var orig = btn.getAttribute('data-orig-html');
                            if(!orig){ orig = btn.innerHTML; btn.setAttribute('data-orig-html', orig); }
                            btn.innerHTML = '<span class="inline-flex items-center gap-2">✅ <span class="hidden sm:inline">Copied!</span></span>';
                            btn.classList.add('ring-2','ring-green-400');
                            setTimeout(function(){ btn.innerHTML = orig; btn.classList.remove('ring-2','ring-green-400'); }, 1500);
                        }catch(e){}
                    });
                }
                // Bind after DOM is ready and after HTMX swaps content inside the modal
                if (document.readyState === 'loading') {
                    document.addEventListener('DOMContentLoaded', function(){ setTimeout(attachDecklistShareHandler, 50); });
                } else {
                    setTimeout(attachDecklistShareHandler, 50);
                }
                document.addEventListener('htmx:afterSwap', function(evt){
                    if (evt.target && evt.target.id === 'selected-tournament-decklist-content-modal') {
                        setTimeout(attachDecklistShareHandler, 10);
                    }
                });
            })();

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