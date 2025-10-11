from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, ExtendedCardData
from op_tcg.frontend_fasthtml.pages.card_popularity import HX_INCLUDE
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner

def create_card_modal(card: ExtendedCardData, card_versions: list[ExtendedCardData], popularity: float, currency: CardCurrency, prev_card_id: str = None, next_card_id: str = None, card_elements: list[str] = None) -> ft.Div:
    """Create a modal dialog for displaying card details.
    
    Args:
        card: The base card data to display
        card_versions: List of all versions of the card (including alt arts)
        popularity: The card's popularity (0-1)
        currency: The selected currency for price display
        prev_card_id: ID of the previous card in the grid
        next_card_id: ID of the next card in the grid
        
    Returns:
        A FastHTML Div containing the modal dialog
    """
    # Helper function to create a key fact row
    def create_key_fact(label: str, value: str | None, icon: str = None) -> ft.Div:
        if value is None:
            return None
        return ft.Div(
            ft.Div(
                ft.I(icon, cls="text-gray-400") if icon else None,
                ft.Span(label, cls="text-gray-400 ml-2 mr-2"),
                cls="flex items-center"
            ),
            ft.Span(value, cls="text-white font-medium"),
            cls="flex justify-between items-center py-2 border-b border-gray-700"
        )

    # Create carousel items starting with the base card
    carousel_items = [
        ft.Div(
            ft.Img(
                src=card.image_url,
                alt=f"{card.name} ({card.id})",
                cls="w-full h-auto rounded-lg shadow-lg"
            ),
            # Left click area for card version navigation (invisible overlay)
            ft.Div(
                cls="absolute left-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                onclick="previousCarouselItem(this)",
                title="Previous version"
            ) if len(card_versions) > 0 else None,
            # Right click area for card version navigation (invisible overlay)
            ft.Div(
                cls="absolute right-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                onclick="nextCarouselItem(this)",
                title="Next version"
            ) if len(card_versions) > 0 else None,
            cls="carousel-item active relative",
            id="carousel-item-base",
            data_price=f"{card.latest_eur_price:.2f}" if currency == CardCurrency.EURO and card.latest_eur_price else 
                      f"{card.latest_usd_price:.2f}" if currency == CardCurrency.US_DOLLAR and card.latest_usd_price else "N/A",
            data_currency="EUR" if currency == CardCurrency.EURO else "USD",
            data_eur_price=f"{card.latest_eur_price:.2f}" if card.latest_eur_price else "N/A",
            data_usd_price=f"{card.latest_usd_price:.2f}" if card.latest_usd_price else "N/A"
        )
    ]
    
    # Add alternate art versions
    for i, version in enumerate(card_versions):
        carousel_items.append(
            ft.Div(
                ft.Img(
                    src=version.image_url,
                    alt=f"{version.name} ({version.id})",
                    cls="w-full h-auto rounded-lg shadow-lg"
                ),
                # Left click area for card version navigation (invisible overlay)
                ft.Div(
                    cls="absolute left-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                    onclick="previousCarouselItem(this)",
                    title="Previous version"
                ),
                # Right click area for card version navigation (invisible overlay)
                ft.Div(
                    cls="absolute right-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                    onclick="nextCarouselItem(this)",
                    title="Next version"
                ),
                cls="carousel-item relative",
                id=f"carousel-item-{i}",
                data_price=f"{version.latest_eur_price:.2f}" if currency == CardCurrency.EURO and version.latest_eur_price else 
                          f"{version.latest_usd_price:.2f}" if currency == CardCurrency.US_DOLLAR and version.latest_usd_price else "N/A",
                data_currency="EUR" if currency == CardCurrency.EURO else "USD",
                data_eur_price=f"{version.latest_eur_price:.2f}" if version.latest_eur_price else "N/A",
                data_usd_price=f"{version.latest_usd_price:.2f}" if version.latest_usd_price else "N/A"
            )
        )

    # Create carousel navigation
    carousel_nav = []
    if len(card_versions) > 0:  # Changed condition since we always have at least the base card
        carousel_nav = [
            # Dots navigation
            ft.Div(
                *[
                    ft.Button(
                        "",
                        cls=f"w-2 h-2 rounded-full {'bg-white' if i == 0 else 'bg-white/50'} hover:bg-white/75 transition-colors",
                        onclick=f"showCarouselItem(this, {i})"
                    )
                    for i in range(len(carousel_items))
                ],
                cls="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2"
            )
        ]

    # Get the price symbol based on currency
    price_symbol = "€" if currency == CardCurrency.EURO else "$"
    price_label = "Price (EUR)" if currency == CardCurrency.EURO else "Price (USD)"

    # Format the initial price display - show both currencies when available
    initial_price = "N/A"
    if card.latest_eur_price and card.latest_usd_price:
        initial_price = f"€{card.latest_eur_price:.2f} | ${card.latest_usd_price:.2f}"
        price_label = "Price (EUR | USD)"
        price_symbol = "💰"
    elif currency == CardCurrency.EURO and card.latest_eur_price:
        initial_price = f"€{card.latest_eur_price:.2f}"
    elif currency == CardCurrency.US_DOLLAR and card.latest_usd_price:
        initial_price = f"${card.latest_usd_price:.2f}"
    elif card.latest_eur_price:
        initial_price = f"€{card.latest_eur_price:.2f}"
    elif card.latest_usd_price:
        initial_price = f"${card.latest_usd_price:.2f}"

    return ft.Div(
        # Modal backdrop
        ft.Div(
            # Single modal content container
            ft.Div(
                # Close button (styled consistent with decklist modal)
                ft.Button(
                    ft.Span("×", cls="text-lg"),
                    type="button",
                    cls="absolute top-4 right-4 inline-flex items-center justify-center w-9 h-9 rounded-full bg-gray-700/60 hover:bg-gray-700 text-white shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-indigo-400 transition z-30",
                    onclick="event.stopPropagation(); closeCardModal();"
                ),
                
                # Card navigation areas (full height on left and right sides)
                ft.Div(
                    cls="absolute left-0 top-0 w-16 h-full cursor-pointer z-10 card-nav-left",
                    hx_get=f"/api/card-modal?card_id={prev_card_id}&card_elements={'&card_elements='.join([c for c in card_elements])}&meta_format=latest" if prev_card_id and card_elements else None,
                    hx_target="body",
                    hx_swap="beforeend",
                    hx_include=HX_INCLUDE,
                    title="Previous Card",
                    style="display: none" if not prev_card_id else None,
                    **{"hx-on::before-request": "document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());"}
                ) if prev_card_id else None,
                
                ft.Div(
                    cls="absolute right-0 top-0 w-16 h-full cursor-pointer z-10 card-nav-right",
                    hx_get=f"/api/card-modal?card_id={next_card_id}&card_elements={'&card_elements='.join([c for c in card_elements])}&meta_format=latest" if next_card_id and card_elements else None,
                    hx_target="body",
                    hx_swap="beforeend",
                    hx_include=HX_INCLUDE,
                    title="Next Card",
                    style="display: none" if not next_card_id else None,
                    **{"hx-on::before-request": "document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());"}
                ) if next_card_id else None,
                
                # Main card content section
                ft.Div(
                    # Card image carousel
                    ft.Div(
                        *carousel_items,
                        *carousel_nav,
                        cls="md:w-1/2 relative"
                    ),
                    # Card details
                    ft.Div(
                        # Card name and ID
                        ft.H2(
                            ft.Span(card.name, cls="text-2xl font-bold text-white"),
                            ft.Span(f" ({card.id})", cls="text-gray-400 text-lg"),
                            cls="mb-6"
                        ),
                        # Key facts container
                        ft.Div(
                            # Type
                            create_key_fact("Type", card.card_category, "🎴"),
                            # Subtype
                            create_key_fact("Subtype", ", ".join(card.types) if card.types else None, "🏷️"),
                            # Colors
                            create_key_fact("Colors", ", ".join(card.colors), "🎨"),
                            # Attributes
                            create_key_fact("Attributes", ", ".join(card.attributes) if card.attributes else None, "⚡"),
                            # Cost
                            create_key_fact("Cost", str(card.cost) if card.cost is not None else None, "💎"),
                            # Power
                            create_key_fact("Power", str(card.power) if card.power is not None else None, "💪"),
                            # Counter
                            create_key_fact("Counter", str(card.counter) if card.counter is not None else None, "🛡️"),
                            # Price
                            ft.Div(
                                ft.Div(
                                    ft.I(price_symbol, cls="text-gray-400"),
                                    ft.Span(price_label, cls="text-gray-400 ml-2 mr-2"),
                                    cls="flex items-center"
                                ),
                                ft.Span(
                                    initial_price,
                                    cls="text-white font-medium",
                                    id="card-price"
                                ),
                                cls="flex justify-between items-center py-2 border-b border-gray-700"
                            ),
                            # Ability
                            create_key_fact("Ability", card.ability, "✨"),
                            # Popularity
                            ft.Div(
                                ft.Div(
                                    ft.I("📊", cls="text-gray-400"),
                                    ft.Span("Popularity", cls="text-gray-400 ml-2 mr-2"),
                                    cls="flex items-center"
                                ),
                                ft.Div(
                                    ft.Div(
                                        ft.Span(
                                            f"{int(popularity * 100)}%",
                                            cls="text-white text-sm ml-5"
                                        ),
                                        cls="progress-bar",
                                        style=f"width: {max(popularity * 100, 5)}%"
                                    ),
                                    cls="progress-container"
                                ),
                                cls="flex justify-between items-center py-2"
                            ),
                            cls="space-y-2 bg-gray-800/50 rounded-lg p-4"
                        ),
                        cls="md:w-1/2 text-white space-y-6"
                    ),
                    cls="flex flex-col md:flex-row gap-6 mb-6"
                ),
                
                # Card occurrence chart section
                ft.Div(
                    ft.Div(
                        ft.H3("Card Occurrence by Leader", cls="text-lg font-semibold text-white mb-4"),
                        # Toggle for absolute vs normalized data
                        ft.Div(
                            ft.Label(
                                ft.Input(
                                    type="checkbox",
                                    id=f"normalize-toggle-{card.id}",
                                    cls="sr-only",
                                    hx_get=f"/api/card-occurrence-chart?card_id={card.id}&meta_format={card.meta_format}",
                                    hx_target=f"#occurrence-chart-container-{card.id}",
                                    hx_include=f"#{f'normalize-toggle-{card.id}'}",
                                    hx_indicator=f"#occurrence-chart-loading-{card.id}",
                                    hx_vals='js:{"normalized": document.getElementById("normalize-toggle-' + card.id + '").checked.toString()}'
                                ),
                                ft.Div(
                                    ft.Div(cls="toggle-thumb"),
                                    cls="toggle-track"
                                ),
                                ft.Span("Show normalized data", cls="text-white ml-3 text-sm"),
                                cls="flex items-center cursor-pointer",
                                for_=f"normalize-toggle-{card.id}"
                            ),
                            cls="flex justify-end mb-4"
                        ),
                        cls="flex justify-between items-start mb-4"
                    ),
                    ft.Div(
                        id=f"occurrence-chart-container-{card.id}",
                        hx_get=f"/api/card-occurrence-chart?card_id={card.id}&meta_format={card.meta_format}",
                        hx_trigger="load",
                        hx_indicator=f"#occurrence-chart-loading-{card.id}",
                        cls="min-h-[300px]"
                    ),
                    create_loading_spinner(
                        id=f"occurrence-chart-loading-{card.id}",
                        size="w-8 h-8",
                        container_classes="min-h-[300px]"
                    ),
                    cls="w-full mb-6"
                ),
                
                # Price development chart section
                ft.Div(
                    ft.Div(
                        ft.H3("Price Development", cls="text-lg font-semibold text-white mb-4"),
                        # Time period selector
                        ft.Div(
                            ft.Select(
                                ft.Option("30 days", value="30"),
                                ft.Option("60 days", value="60"),
                                ft.Option("90 days", value="90", selected=True),
                                ft.Option("180 days", value="180"),
                                ft.Option("365 days", value="365"),
                                id=f"price-period-selector-{card.id}",
                                cls="bg-gray-700 text-white border border-gray-600 rounded px-3 py-1 text-sm",
                                hx_get=f"/api/card-price-development-chart",
                                hx_target=f"#price-chart-container-{card.id}",
                                hx_indicator=f"#price-chart-loading-{card.id}",
                                hx_vals=f'js:{{"card_id": "{card.id}", "days": document.getElementById("price-period-selector-{card.id}").value, "include_alt_art": "false"}}',
                                **{"hx-on::before-request": f"document.getElementById('price-chart-container-{card.id}').innerHTML = ''; document.getElementById('price-chart-loading-{card.id}').style.display = 'flex';"}
                            ),
                            cls="flex justify-end mb-4"
                        ),
                        cls="flex justify-between items-start mb-4"
                    ),
                    ft.Div(
                        id=f"price-chart-container-{card.id}",
                        hx_get=f"/api/card-price-development-chart?card_id={card.id}&days=90",
                        hx_trigger="load",
                        hx_indicator=f"#price-chart-loading-{card.id}",
                        cls="min-h-[300px]"
                    ),
                    create_loading_spinner(
                        id=f"price-chart-loading-{card.id}",
                        size="w-8 h-8",
                        container_classes="min-h-[300px]"
                    ),
                    cls="w-full"
                ),
                
                cls="bg-gray-800 rounded-lg p-6 max-w-4xl w-full mx-4 relative"
            ),
            cls="modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 overflow-y-auto py-4",
            onclick="if (event.target === this) closeCardModal();",
            data_card_id=card.id
        ),
        # Carousel and URL management JavaScript
        ft.Script("""
            // URL management for card modal sharing
            function updateURLWithCardId(cardId) {
                const url = new URL(window.location);
                // Only change pathname if not already on card-popularity page
                if (!url.pathname.includes('card-popularity')) {
                    url.pathname = '/card-popularity';
                }
                url.searchParams.set('card_id', cardId);
                window.history.pushState({cardId: cardId}, '', url);
            }
            
            function removeCardIdFromURL() {
                const url = new URL(window.location);
                url.searchParams.delete('card_id');
                window.history.replaceState({}, '', url);
            }
            
            function closeCardModal() {
                document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());
                removeCardIdFromURL();
            }
            
            // Update URL when modal is opened via HTMX
            document.addEventListener('htmx:afterSettle', function(evt) {
                // Check if a modal backdrop was added to the body
                const modalBackdrop = document.querySelector('.modal-backdrop[data-card-id]');
                if (modalBackdrop && evt.detail.target === document.body) {
                    const cardId = modalBackdrop.getAttribute('data-card-id');
                    if (cardId) {
                        updateURLWithCardId(cardId);
                    }
                }
            });
            
            // Handle browser back/forward buttons
            window.addEventListener('popstate', function(event) {
                const url = new URL(window.location);
                const cardId = url.searchParams.get('card_id');
                
                if (!cardId) {
                    // Close modal if card_id is removed from URL
                    document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove());
                }
            });
            
            function getCarouselContainer(element) {
                return element.closest('.modal-backdrop').querySelector('.carousel-item').parentElement;
            }
            
            function updatePrice(activeItem) {
                const priceElement = document.getElementById('card-price');
                if (priceElement) {
                    const price = activeItem.getAttribute('data-price');
                    const currency = activeItem.getAttribute('data-currency');
                    const eurPrice = activeItem.getAttribute('data-eur-price');
                    const usdPrice = activeItem.getAttribute('data-usd-price');
                    
                    if (eurPrice && usdPrice && eurPrice !== 'N/A' && usdPrice !== 'N/A') {
                        // Show both currencies when available
                        priceElement.textContent = `€${eurPrice} | $${usdPrice}`;
                    } else if (price === 'N/A') {
                        priceElement.textContent = 'N/A';
                    } else {
                        priceElement.textContent = currency === 'EUR' ? 
                            `€${price}` : 
                            `$${price}`;
                    }
                }
            }
            
            function showCarouselItem(element, index) {
                const container = getCarouselContainer(element);
                const items = container.querySelectorAll('.carousel-item');
                const dots = container.querySelectorAll('.carousel-dot');
                
                items.forEach(item => item.classList.remove('active'));
                items[index].classList.add('active');
                
                // Update price for the active item
                updatePrice(items[index]);
                
                if (dots.length > 0) {
                    dots.forEach((dot, i) => {
                        dot.classList.toggle('bg-white', i === index);
                        dot.classList.toggle('bg-white/50', i !== index);
                    });
                }
            }
            
            function nextCarouselItem(element) {
                const container = getCarouselContainer(element);
                const items = container.querySelectorAll('.carousel-item');
                const currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
                const nextIndex = (currentIndex + 1) % items.length;
                showCarouselItem(element, nextIndex);
            }
            
            function previousCarouselItem(element) {
                const container = getCarouselContainer(element);
                const items = container.querySelectorAll('.carousel-item');
                const currentIndex = Array.from(items).findIndex(item => item.classList.contains('active'));
                const prevIndex = (currentIndex - 1 + items.length) % items.length;
                showCarouselItem(element, prevIndex);
            }
            
            // Add keyboard navigation
            document.addEventListener('keydown', (e) => {
                const activeModal = document.querySelector('.modal-backdrop');
                if (!activeModal) return;
                
                if (e.key === 'ArrowLeft') {
                    previousCarouselItem(activeModal);
                } else if (e.key === 'ArrowRight') {
                    nextCarouselItem(activeModal);
                }
            });
            
            // Add touch support for mobile card navigation
            document.addEventListener('DOMContentLoaded', function() {
                const cardNavLeft = document.querySelector('.card-nav-left');
                const cardNavRight = document.querySelector('.card-nav-right');
                
                if (cardNavLeft) {
                    cardNavLeft.addEventListener('touchstart', function(e) {
                        e.preventDefault();
                        this.click();
                    });
                }
                
                if (cardNavRight) {
                    cardNavRight.addEventListener('touchstart', function(e) {
                        e.preventDefault();
                        this.click();
                    });
                }
            });
        """),
        # Carousel CSS
        ft.Style("""
            .carousel-item {
                display: none;
                opacity: 0;
                transition: opacity 0.3s ease;
            }
            .carousel-item.active {
                display: block;
                opacity: 1;
            }
            
            /* Card version navigation hover effects (for alt art carousel) */
            .card-version-nav:hover {
                background: rgba(255, 255, 255, 0.1);
                transition: background 0.2s ease;
                z-index: 30; /* Ensure version navigation is always on top */
            }
            
            /* Add subtle visual indicators on hover for version navigation */
            .card-version-nav:first-of-type:hover::after {
                content: '◀';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 1.5rem;
                text-shadow: 0 0 4px rgba(0, 0, 0, 0.8);
                pointer-events: none;
                z-index: 31;
            }
            
            .card-version-nav:last-of-type:hover::after {
                content: '▶';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 1.5rem;
                text-shadow: 0 0 4px rgba(0, 0, 0, 0.8);
                pointer-events: none;
                z-index: 31;
            }
            
            /* Card navigation hover effects - only active outside image area */
            .card-nav-left:hover {
                background: linear-gradient(to right, rgba(0, 0, 0, 0.4), transparent);
                transition: background 0.2s ease;
            }
            
            .card-nav-right:hover {
                background: linear-gradient(to left, rgba(0, 0, 0, 0.4), transparent);
                transition: background 0.2s ease;
            }
            
            /* Card navigation arrows on hover - only show outside image area */
            .card-nav-left:hover::after {
                content: '◀ Previous';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 1.2rem;
                font-weight: bold;
                text-shadow: 0 0 8px rgba(0, 0, 0, 0.9);
                pointer-events: none;
                white-space: nowrap;
            }
            
            .card-nav-right:hover::after {
                content: 'Next ▶';
                position: absolute;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                color: white;
                font-size: 1.2rem;
                font-weight: bold;
                text-shadow: 0 0 8px rgba(0, 0, 0, 0.9);
                pointer-events: none;
                white-space: nowrap;
            }
            
            /* Ensure card navigation doesn't interfere with image area on desktop */
            @media (min-width: 769px) {
                .card-nav-left {
                    /* Only show on the left margin area, not overlapping with image */
                    width: 64px;
                    background: transparent;
                }
                
                .card-nav-right {
                    /* Only show on the right margin area, not overlapping with image */
                    width: 64px;
                    background: transparent;
                }
                
                /* Hide card navigation arrows when hovering over image area */
                .md\\:w-1\\/2:hover ~ .card-nav-left,
                .md\\:w-1\\/2:hover ~ .card-nav-right {
                    pointer-events: none;
                    opacity: 0.3;
                }
            }
            
            /* Toggle switch styles */
            .toggle-track {
                width: 44px;
                height: 24px;
                background-color: #4B5563;
                border-radius: 12px;
                position: relative;
                transition: background-color 0.3s ease;
            }
            
            .toggle-thumb {
                width: 20px;
                height: 20px;
                background-color: white;
                border-radius: 50%;
                position: absolute;
                top: 2px;
                left: 2px;
                transition: transform 0.3s ease;
                box-shadow: 0 2px 4px rgba(0, 0, 0, 0.2);
            }
            
            /* Toggle checked state */
            input[type="checkbox"]:checked + .toggle-track {
                background-color: #10B981;
            }
            
            input[type="checkbox"]:checked + .toggle-track .toggle-thumb {
                transform: translateX(20px);
            }
            
            /* Mobile-specific styles */
            @media (max-width: 768px) {
                .modal-backdrop {
                    align-items: flex-start !important;
                    padding: 1rem 0;
                }
                .modal-backdrop > div {
                    margin: 0 1rem;
                    max-height: none;
                    min-height: calc(100vh - 2rem);
                    width: calc(100% - 2rem);
                }
                .modal-backdrop > div > div:first-of-type {
                    flex-direction: column;
                }
                .modal-backdrop > div > div:first-of-type .md\\:w-1\\/2 {
                    width: 100%;
                }
                
                /* Adjust card navigation for mobile - make them wider for easier touch */
                .card-nav-left, .card-nav-right {
                    width: 80px; /* Increased width for easier touch */
                }
                
                /* Add visual feedback for touch on mobile */
                .card-nav-left:active {
                    background: linear-gradient(to right, rgba(0, 0, 0, 0.6), transparent);
                }
                
                .card-nav-right:active {
                    background: linear-gradient(to left, rgba(0, 0, 0, 0.6), transparent);
                }
                
                /* Show navigation indicators on mobile without hover */
                .card-nav-left::before {
                    content: '◀';
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: rgba(255, 255, 255, 0.3);
                    font-size: 1.5rem;
                    font-weight: bold;
                    text-shadow: 0 0 8px rgba(0, 0, 0, 0.9);
                    pointer-events: none;
                }
                
                .card-nav-right::before {
                    content: '▶';
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    color: rgba(255, 255, 255, 0.3);
                    font-size: 1.5rem;
                    font-weight: bold;
                    text-shadow: 0 0 8px rgba(0, 0, 0, 0.9);
                    pointer-events: none;
                }
                
                /* Adjust navigation text for mobile */
                .card-nav-left:hover::after {
                    content: '◀';
                    font-size: 2rem; /* Larger for mobile */
                }
                
                .card-nav-right:hover::after {
                    content: '▶';
                    font-size: 2rem; /* Larger for mobile */
                }
            }
            
            /* Desktop-specific styles */
            @media (min-width: 769px) {
                .modal-backdrop {
                    align-items: center;
                    justify-content: center;
                }
                .modal-backdrop > div {
                    max-height: 90vh;
                    overflow-y: auto;
                }
            }
            
            /* Chart container overflow prevention */
            .bg-gray-800\\/30 {
                overflow: hidden;
            }
            
            /* Ensure chart legend stays within bounds */
            canvas {
                max-width: 100% !important;
                height: auto !important;
            }
        """)
    )
