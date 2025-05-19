from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, ExtendedCardData
from op_tcg.frontend_fasthtml.pages.card_popularity import HX_INCLUDE

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
            cls="carousel-item active",
            id="carousel-item-base",
            data_price=f"{card.latest_eur_price:.2f}" if currency == CardCurrency.EURO and card.latest_eur_price else 
                      f"{card.latest_usd_price:.2f}" if currency == CardCurrency.US_DOLLAR and card.latest_usd_price else "N/A",
            data_currency="EUR" if currency == CardCurrency.EURO else "USD"
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
                cls="carousel-item",
                id=f"carousel-item-{i}",
                data_price=f"{version.latest_eur_price:.2f}" if currency == CardCurrency.EURO and version.latest_eur_price else 
                          f"{version.latest_usd_price:.2f}" if currency == CardCurrency.US_DOLLAR and version.latest_usd_price else "N/A",
                data_currency="EUR" if currency == CardCurrency.EURO else "USD"
            )
        )

    # Create carousel navigation
    carousel_nav = []
    if len(card_versions) > 0:  # Changed condition since we always have at least the base card
        carousel_nav = [
            # Previous button
            ft.Button(
                ft.I("←", cls="text-2xl"),
                cls="absolute left-2 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/75 transition-colors",
                onclick="previousCarouselItem(this)"
            ),
            # Next button
            ft.Button(
                ft.I("→", cls="text-2xl"),
                cls="absolute right-2 top-1/2 -translate-y-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/75 transition-colors",
                onclick="nextCarouselItem(this)"
            ),
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

    # Format the initial price display
    initial_price = "N/A"
    if currency == CardCurrency.EURO and card.latest_eur_price:
        initial_price = f"{card.latest_eur_price:.2f} €"
    elif currency == CardCurrency.US_DOLLAR and card.latest_usd_price:
        initial_price = f"${card.latest_usd_price:.2f}"

    # Create navigation buttons for previous/next card only if we have the IDs
    card_nav = []
    if prev_card_id or next_card_id:
        card_nav = [
            # Previous card button
            ft.Button(
                ft.I("◀", cls="text-2xl"),
                cls="absolute left-0 top-1/2 -translate-y-1/2 -translate-x-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/75 transition-colors",
                hx_get=f"/api/card-modal?card_id={prev_card_id}&card_elements={'&card_elements='.join([c for c in card_elements])}" if prev_card_id else None,
                hx_target="body",
                hx_swap="beforeend",
                hx_include=HX_INCLUDE,
                data_tooltip="Previous Card",
                style="display: none" if not prev_card_id else None
            ),
            # Next card button
            ft.Button(
                ft.I("▶", cls="text-2xl"),
                cls="absolute right-0 top-1/2 -translate-y-1/2 translate-x-1/2 bg-black/50 text-white p-2 rounded-full hover:bg-black/75 transition-colors",
                hx_get=f"/api/card-modal?card_id={next_card_id}&card_elements={'&card_elements='.join([c for c in card_elements])}" if next_card_id else None,
                hx_target="body",
                hx_swap="beforeend",
                hx_include=HX_INCLUDE,
                data_tooltip="Next Card",
                style="display: none" if not next_card_id else None
            ),
        ]

    return ft.Div(
        # Modal backdrop
        ft.Div(
            # Modal content
            ft.Div(
                # Close button
                ft.Button(
                    ft.I("×", cls="text-2xl"),
                    cls="absolute top-4 right-4 text-gray-400 hover:text-white transition-colors z-10",
                    onclick="document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove())"
                ),
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
                # Navigation buttons for previous/next card
                *card_nav,
                cls="bg-gray-800 rounded-lg p-6 max-w-4xl w-full mx-4 flex flex-col md:flex-row gap-6 relative"
            ),
            cls="modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center z-50 overflow-y-auto py-4",
            onclick="if (event.target === this) document.querySelectorAll('.modal-backdrop').forEach(modal => modal.remove())"
        ),
        # Carousel JavaScript
        ft.Script("""
            function getCarouselContainer(element) {
                return element.closest('.modal-backdrop').querySelector('.carousel-item').parentElement;
            }
            
            function updatePrice(activeItem) {
                const priceElement = document.getElementById('card-price');
                if (priceElement) {
                    const price = activeItem.getAttribute('data-price');
                    const currency = activeItem.getAttribute('data-currency');
                    
                    if (price === 'N/A') {
                        priceElement.textContent = 'N/A';
                    } else {
                        priceElement.textContent = currency === 'EUR' ? 
                            `${price} €` : 
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
            
            /* Mobile-specific styles */
            @media (max-width: 768px) {
                .modal-backdrop {
                    align-items: flex-start;
                }
                .modal-backdrop > div {
                    margin: 1rem;
                    max-height: calc(100vh - 2rem);
                    overflow-y: auto;
                }
            }
        """)
    ) 