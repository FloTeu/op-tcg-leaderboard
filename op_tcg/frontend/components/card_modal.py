from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, ExtendedCardData
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.effect_text import render_effect_text
from op_tcg.frontend.components.watchlist_toggle import create_watchlist_toggle
from op_tcg.frontend.utils.card_price import get_marketplace_link

_ROW_CLS = "flex justify-between items-center py-2"
_ROW_STYLE = "border-bottom:1px solid #1a2540;"
_LABEL_STYLE = "font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.65rem; color:#475569; text-transform:uppercase;"
_VALUE_STYLE = "font-family:'Share Tech Mono',monospace; font-size:0.8rem; color:#f1f5f9;"


def create_card_modal(card: ExtendedCardData, card_versions: list[ExtendedCardData], popularity: float,
                      currency: CardCurrency, selected_aa_version: int = 0, watched_versions: set = None,
                      is_logged_in: bool = False) -> ft.Div:
    """Create a modal dialog for displaying card details."""
    if watched_versions is None:
        watched_versions = set()

    def create_key_fact(label: str, value: str | None, icon: str = None) -> ft.Div:
        if value is None:
            return None
        return ft.Div(
            ft.Span(label, style=_LABEL_STYLE),
            ft.Span(value, style=_VALUE_STYLE),
            cls=_ROW_CLS,
            style=_ROW_STYLE,
        )

    selected_card = card
    if selected_aa_version > 0:
        for v in card_versions:
            if v.aa_version == selected_aa_version:
                selected_card = v
                break

    cm_url, _ = get_marketplace_link(card, CardCurrency.EURO)
    tcg_url, _ = get_marketplace_link(card, CardCurrency.US_DOLLAR)

    is_base_active = (card.aa_version == selected_aa_version)
    base_cls = "carousel-item active relative" if is_base_active else "carousel-item relative"
    base_in_watchlist = card.aa_version in watched_versions

    carousel_items = [
        ft.Div(
            ft.Img(
                src=card.image_url,
                alt=f"{card.name} ({card.id})",
                cls="w-full h-auto rounded-lg shadow-lg"
            ),
            ft.Div(
                cls="absolute left-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                onclick="window.previousCarouselItem(this)",
                title="Previous version"
            ) if len(card_versions) > 0 else None,
            ft.Div(
                cls="absolute right-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                onclick="window.nextCarouselItem(this)",
                title="Next version"
            ) if len(card_versions) > 0 else None,
            cls=base_cls,
            id="carousel-item-base",
            data_card_id=card.id,
            data_aa_version=card.aa_version,
            data_in_watchlist="true" if base_in_watchlist else "false",
            data_price=f"{card.latest_eur_price:.2f}" if currency == CardCurrency.EURO and card.latest_eur_price else
            f"{card.latest_usd_price:.2f}" if currency == CardCurrency.US_DOLLAR and card.latest_usd_price else "N/A",
            data_currency=CardCurrency.EURO if currency == CardCurrency.EURO else CardCurrency.US_DOLLAR,
            data_eur_price=f"{card.latest_eur_price:.2f}" if card.latest_eur_price else "N/A",
            data_usd_price=f"{card.latest_usd_price:.2f}" if card.latest_usd_price else "N/A",
            data_cm_url=cm_url,
            data_tcg_url=tcg_url
        )
    ]

    for i, version in enumerate(card_versions):
        v_cm_url, _ = get_marketplace_link(version, CardCurrency.EURO)
        v_tcg_url, _ = get_marketplace_link(version, CardCurrency.US_DOLLAR)
        is_active = (version.aa_version == selected_aa_version)
        item_cls = "carousel-item active relative" if is_active else "carousel-item relative"
        version_in_watchlist = version.aa_version in watched_versions

        carousel_items.append(
            ft.Div(
                ft.Img(
                    src=version.image_url,
                    alt=f"{version.name} ({version.id})",
                    cls="w-full h-auto rounded-lg shadow-lg"
                ),
                ft.Div(
                    cls="absolute left-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                    onclick="window.previousCarouselItem(this)",
                    title="Previous version"
                ),
                ft.Div(
                    cls="absolute right-0 top-0 w-1/3 h-full cursor-pointer z-20 card-version-nav",
                    onclick="window.nextCarouselItem(this)",
                    title="Next version"
                ),
                cls=item_cls,
                id=f"carousel-item-{i}",
                data_card_id=version.id,
                data_aa_version=version.aa_version,
                data_in_watchlist="true" if version_in_watchlist else "false",
                data_price=f"{version.latest_eur_price:.2f}" if currency == CardCurrency.EURO and version.latest_eur_price else
                f"{version.latest_usd_price:.2f}" if currency == CardCurrency.US_DOLLAR and version.latest_usd_price else "N/A",
                data_currency=CardCurrency.EURO if currency == CardCurrency.EURO else CardCurrency.US_DOLLAR,
                data_eur_price=f"{version.latest_eur_price:.2f}" if version.latest_eur_price else "N/A",
                data_usd_price=f"{version.latest_usd_price:.2f}" if version.latest_usd_price else "N/A",
                data_cm_url=v_cm_url,
                data_tcg_url=v_tcg_url
            )
        )

    carousel_nav = []
    if len(card_versions) > 0:
        carousel_nav = [
            ft.Div(
                *[
                    ft.Button(
                        "",
                        cls=f"w-2 h-2 rounded-full transition-colors",
                        style=f"background:{'#38bdf8' if i == 0 else 'rgba(56,189,248,0.3)'}; border:none; cursor:pointer;",
                        onclick=f"window.showCarouselItem(this, {i})"
                    )
                    for i in range(len(carousel_items))
                ],
                cls="absolute bottom-4 left-1/2 -translate-x-1/2 flex gap-2"
            )
        ]

    price_symbol = "€" if currency == CardCurrency.EURO else "$"
    price_label = "Price (EUR)" if currency == CardCurrency.EURO else "Price (USD)"

    cm_url, _ = get_marketplace_link(selected_card, CardCurrency.EURO)
    tcg_url, _ = get_marketplace_link(selected_card, CardCurrency.US_DOLLAR)

    initial_price = "N/A"
    if selected_card.latest_eur_price and selected_card.latest_usd_price:
        initial_price = f"€{selected_card.latest_eur_price:.2f} | ${selected_card.latest_usd_price:.2f}"
        price_label = "Price (EUR | USD)"
        price_symbol = "💰"
    elif currency == CardCurrency.EURO and selected_card.latest_eur_price:
        initial_price = f"€{selected_card.latest_eur_price:.2f}"
    elif currency == CardCurrency.US_DOLLAR and selected_card.latest_usd_price:
        initial_price = f"${selected_card.latest_usd_price:.2f}"
    elif selected_card.latest_eur_price:
        initial_price = f"€{selected_card.latest_eur_price:.2f}"
    elif selected_card.latest_usd_price:
        initial_price = f"${selected_card.latest_usd_price:.2f}"

    initial_in_watchlist = selected_card.aa_version in watched_versions

    return ft.Div(
        ft.Div(
            ft.Div(
                # Close button
                ft.Button(
                    ft.Span("×", style="font-size:1.2rem; line-height:1;"),
                    type="button",
                    cls="absolute top-4 right-4 md:top-4 md:right-4 inline-flex items-center justify-center w-9 h-9 rounded-full z-30 mobile-close-btn transition",
                    style="background:rgba(8,14,28,0.9); border:1px solid #1a2540; color:#94a3b8;",
                    onclick="event.stopPropagation(); window.closeCardModal();"
                ),

                # Watchlist button
                create_watchlist_toggle(
                    card_id=selected_card.id,
                    card_version=selected_card.aa_version,
                    language="en",
                    is_in_watchlist=initial_in_watchlist,
                    extra_cls="absolute top-4 right-16 md:top-4 md:right-16 z-30 mobile-watchlist-btn",
                    btn_cls="w-9 h-9",
                    include_script=True,
                    is_logged_in=is_logged_in,
                ),

                # Card navigation — previous
                ft.Div(
                    ft.Div("‹", cls="text-white text-4xl font-bold opacity-0 group-hover:opacity-100 transition-opacity"),
                    cls="absolute left-0 top-0 w-16 h-full cursor-pointer z-10 card-nav-left card-nav-top-section flex items-center justify-center hover:bg-black/30 transition-colors group",
                    onclick=f"event.stopPropagation(); window.navigateToPreviousCard('{card.id}', event);",
                    title="Previous card",
                    data_current_card_id=card.id
                ),

                # Card navigation — next
                ft.Div(
                    ft.Div("›", cls="text-white text-4xl font-bold opacity-0 group-hover:opacity-100 transition-opacity"),
                    cls="absolute right-0 top-0 w-16 h-full cursor-pointer z-10 card-nav-right card-nav-top-section flex items-center justify-center hover:bg-black/30 transition-colors group",
                    onclick=f"event.stopPropagation(); window.navigateToNextCard('{card.id}', event);",
                    title="Next card",
                    data_current_card_id=card.id
                ),

                # ── Main content ─────────────────────────────────────────────
                ft.Div(
                    # Card image carousel
                    ft.Div(
                        *carousel_items,
                        *carousel_nav,
                        *(
                            [
                                ft.Div(ft.Div("◀", cls="aa-hint-arrow"), id="aa-hint-left",
                                       cls="aa-hint-side aa-hint-left-side", style="opacity:0; transition: opacity 0.4s ease;"),
                                ft.Div(ft.Div("▶", cls="aa-hint-arrow"), id="aa-hint-right",
                                       cls="aa-hint-side aa-hint-right-side", style="opacity:0; transition: opacity 0.4s ease;"),
                                ft.Div(
                                    ft.Div("✦ Alt art versions available", cls="font-bold text-sm mb-0.5"),
                                    ft.Div("tap ◀ left  or  right ▶ to browse", cls="text-xs text-white/80"),
                                    id="aa-version-hint",
                                    cls="absolute left-1/2 -translate-x-1/2 z-30 pointer-events-none text-center text-white aa-hint-label",
                                    style="top:55%; opacity:0; transition: opacity 0.4s ease;"
                                ),
                                ft.Script("""
(function() {
    var KEY = 'card-aa-hint-seen';
    //if (localStorage.getItem(KEY)) return;
    var hintL = document.getElementById('aa-hint-left');
    var hintR = document.getElementById('aa-hint-right');
    var label = document.getElementById('aa-version-hint');
    if (!hintL || !hintR || !label) return;
    var dismissed = false;
    function dismiss() {
        if (dismissed) return;
        dismissed = true;
        [hintL, hintR, label].forEach(function(el) { el.style.opacity = '0'; });
        localStorage.setItem(KEY, '1');
    }
    setTimeout(function() {
        [hintL, hintR, label].forEach(function(el) { el.style.opacity = '1'; });
        setTimeout(dismiss, 1500);
    }, 600);
    var carousel = hintL.closest('.relative');
    if (carousel) {
        carousel.addEventListener('click', dismiss, { once: true });
    }
})();
"""),
                            ]
                            if len(card_versions) > 0 else []
                        ),
                        cls="md:w-1/2 relative md:self-start"
                    ),

                    # Watchlist carousel sync script (unchanged)
                    ft.Script("""
                        (function() {
                            // Find our button - relying on its unique position class
                            function getWatchlistBtn() {
                                const container = document.querySelector('.modal-backdrop .absolute.top-4.right-16');
                                return container ? container.querySelector('button') : null;
                            }

                            function updateWatchlistButtonState(isInWatchlist) {
                                const btn = getWatchlistBtn();
                                if (!btn) return;
                                const svg = btn.querySelector('svg');

                                // Update dataset so the generic toggle function reads correct state
                                btn.dataset.inWatchlist = isInWatchlist.toString();

                                if (isInWatchlist) {
                                    svg.setAttribute('fill', 'currentColor');
                                    btn.classList.remove('text-gray-400', 'hover:text-red-400');
                                    btn.classList.add('text-red-500');
                                    btn.title = "Remove from Watchlist";
                                } else {
                                    svg.setAttribute('fill', 'none');
                                    btn.classList.add('text-gray-400', 'hover:text-red-400');
                                    btn.classList.remove('text-red-500');
                                    btn.title = "Add to Watchlist";
                                }
                            }

                            // Hook into existing global showCarouselItem
                            const originalShowCarouselItem = window.showCarouselItem;
                            window.showCarouselItem = function(element, index) {
                                if (originalShowCarouselItem) {
                                    originalShowCarouselItem(element, index);
                                }

                                // Update watchlist button based on new active item
                                setTimeout(() => {
                                    // Logic to match the active item
                                    const items = document.querySelectorAll('.carousel-item');
                                    if (items[index]) {
                                         const activeItem = items[index];
                                         const isIn = activeItem.dataset.inWatchlist === 'true';
                                         const cardId = activeItem.dataset.cardId;
                                         const cardVersion = activeItem.dataset.aaVersion;

                                         // Update global button attributes so generic toggle actions the correct card
                                         const btn = getWatchlistBtn();
                                         if (btn) {
                                             btn.dataset.cardId = cardId;
                                             btn.dataset.cardVersion = cardVersion;
                                             // Update visual state
                                             updateWatchlistButtonState(isIn);
                                         }
                                    }
                                }, 50);
                            };

                            // Observe carousel changes for robustness (e.g. if updated by other means)
                             const observer = new MutationObserver((mutations) => {
                                mutations.forEach((mutation) => {
                                    if (mutation.type === 'attributes' && mutation.attributeName === 'class') {
                                        if (mutation.target.classList.contains('active')) {
                                            const activeItem = mutation.target;
                                            const isIn = activeItem.dataset.inWatchlist === 'true';
                                            const cardId = activeItem.dataset.cardId;
                                            const cardVersion = activeItem.dataset.aaVersion;

                                            const btn = getWatchlistBtn();
                                            if (btn) {
                                                 btn.dataset.cardId = cardId;
                                                 btn.dataset.cardVersion = cardVersion;
                                                 updateWatchlistButtonState(isIn);
                                            }
                                        }
                                    }
                                });
                            });

                            document.querySelectorAll('.carousel-item').forEach(item => {
                                observer.observe(item, { attributes: true });
                            });

                            const btn = getWatchlistBtn();
                            if (btn) {
                                btn.addEventListener('click', function() {
                                    setTimeout(() => {
                                        const newState = btn.dataset.inWatchlist;
                                        const activeItem = document.querySelector('.carousel-item.active');
                                        if (activeItem) {
                                            activeItem.dataset.inWatchlist = newState;
                                        }
                                    }, 200);
                                });
                            }

                        })();
                    """),

                    # ── Card details ──────────────────────────────────────────
                    ft.Div(
                        # Name + ID
                        ft.Div(
                            ft.Span(card.name,
                                    style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1.5rem; color:#f1f5f9; line-height:1.1;"),
                            ft.Span(f" {card.id}",
                                    style="font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#475569; margin-left:6px;"),
                            cls="flex flex-wrap items-baseline gap-1 mb-5",
                            style="padding-bottom:12px; border-bottom:1px solid #1a2540;",
                        ),

                        # Key facts
                        ft.Div(
                            create_key_fact("Type", card.card_category),
                            create_key_fact("Subtype", ", ".join(card.types) if card.types else None),
                            create_key_fact("Colors", ", ".join(card.colors)),
                            create_key_fact("Attributes", ", ".join(card.attributes) if card.attributes else None),
                            create_key_fact("Cost", str(card.cost) if card.cost is not None else None),
                            create_key_fact("Power", str(card.power) if card.power is not None else None),
                            create_key_fact("Counter", str(card.counter) if card.counter is not None else None),

                            # Price row
                            ft.Div(
                                ft.Span(price_label, style=_LABEL_STYLE),
                                ft.Span(initial_price, id="card-price",
                                        style="font-family:'Share Tech Mono',monospace; font-size:0.85rem; color:#f59e0b;"),
                                cls=_ROW_CLS, style=_ROW_STYLE,
                            ),

                            # Marketplace row
                            ft.Div(
                                ft.Span("Buy on", style=_LABEL_STYLE),
                                ft.Div(
                                    ft.A("Cardmarket", href=cm_url, target="_blank", rel="noopener",
                                         id="marketplace-link-cm",
                                         style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.08em; font-size:0.75rem; background:#10b981; color:#000; padding:5px 14px; border-radius:6px 0 0 6px; text-decoration:none; transition:background 0.12s; flex:1; text-align:center; display:block;"),
                                    ft.A("TCGPlayer", href=tcg_url, target="_blank", rel="noopener",
                                         id="marketplace-link-tcg",
                                         style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.08em; font-size:0.75rem; background:#38bdf8; color:#000; padding:5px 14px; border-radius:0 6px 6px 0; text-decoration:none; transition:background 0.12s; flex:1; text-align:center; display:block;"),
                                    cls="flex",
                                    style="max-width:200px;",
                                ),
                                cls=_ROW_CLS, style=_ROW_STYLE,
                            ),

                            # Ability row
                            ft.Div(
                                ft.Span("Ability", style=_LABEL_STYLE + " flex-shrink:0; margin-right:12px;"),
                                ft.Div(
                                    render_effect_text(card.ability, subject_name=card.name),
                                    style="font-family:'Barlow',sans-serif; font-size:0.82rem; color:#94a3b8; line-height:1.5; flex:1; text-align:right;",
                                ),
                                cls="flex justify-between items-start py-2",
                                style=_ROW_STYLE,
                            ),

                            # Popularity row
                            ft.Div(
                                ft.Span("Popularity", style=_LABEL_STYLE),
                                ft.Div(
                                    ft.Div(
                                        ft.Span(f"{int(popularity * 100)}%",
                                                style="font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#f1f5f9; padding-right:4px;"),
                                        cls="cm-progress-bar",
                                        style=f"width:{max(popularity * 100, 5)}%;",
                                        data_tooltip="Percentage of same color decks playing this card."
                                    ),
                                    cls="cm-progress-container",
                                    style="flex:1; max-width:160px;",
                                ),
                                cls=_ROW_CLS,
                            ),

                            style="background:#080e1c; border:1px solid #1a2540; border-radius:8px; padding:12px;",
                        ),

                        cls="md:w-1/2 space-y-0",
                    ),

                    cls="flex flex-col md:flex-row gap-6 mb-6",
                ),

                # ── Card Occurrence chart ─────────────────────────────────────
                ft.Div(
                    ft.Div(
                        ft.Span("Card Occurrence by Leader",
                                style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9;"),
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
                                ft.Div(ft.Div(cls="toggle-thumb"), cls="toggle-track"),
                                ft.Span("Normalized",
                                        style="font-family:'Barlow',sans-serif; font-size:0.78rem; color:#475569; margin-left:8px;"),
                                cls="flex items-center cursor-pointer",
                                for_=f"normalize-toggle-{card.id}"
                            ),
                            cls="flex justify-end",
                        ),
                        cls="flex justify-between items-center mb-4",
                    ),
                    ft.Div(
                        id=f"occurrence-chart-container-{card.id}",
                        hx_get=f"/api/card-occurrence-chart?card_id={card.id}&meta_format={card.meta_format}",
                        hx_trigger="load",
                        hx_indicator=f"#occurrence-chart-loading-{card.id}",
                        cls="min-h-[300px]"
                    ),
                    create_loading_spinner(id=f"occurrence-chart-loading-{card.id}", size="w-8 h-8",
                                           container_classes="min-h-[300px]"),
                    cls="w-full mb-6",
                    style="padding-top:20px; border-top:1px solid #1a2540;",
                ),

                # ── Price Development chart ───────────────────────────────────
                ft.Div(
                    ft.Div(
                        ft.Span("Price Development",
                                style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9;"),
                        ft.Select(
                            ft.Option("30 days", value="30"),
                            ft.Option("60 days", value="60"),
                            ft.Option("90 days", value="90", selected=True),
                            ft.Option("180 days", value="180"),
                            ft.Option("365 days", value="365"),
                            id=f"price-period-selector-{card.id}",
                            style="background:#080e1c; color:#f1f5f9; border:1px solid #1a2540; border-radius:6px; padding:4px 10px; font-family:'Barlow',sans-serif; font-size:0.8rem; outline:none; cursor:pointer;",
                            hx_get=f"/api/card-price-development-chart",
                            hx_target=f"#price-chart-container-{card.id}",
                            hx_indicator=f"#price-chart-loading-{card.id}",
                            hx_vals=f'js:{{"card_id": "{card.id}", "days": document.getElementById("price-period-selector-{card.id}").value, "include_alt_art": "false", "aa_version": "{selected_aa_version}", "location": "modal"}}',
                            **{
                                "hx-on::before-request": f"document.getElementById('price-chart-container-{card.id}').innerHTML = ''; document.getElementById('price-chart-loading-{card.id}').style.display = 'flex';"}
                        ),
                        cls="flex justify-between items-center mb-4",
                    ),
                    ft.Div(
                        id=f"price-chart-container-{card.id}",
                        hx_get=f"/api/card-price-development-chart?card_id={card.id}&days=90&aa_version={selected_aa_version}&location=modal",
                        hx_trigger="load",
                        hx_indicator=f"#price-chart-loading-{card.id}",
                        cls="min-h-[300px]"
                    ),
                    create_loading_spinner(id=f"price-chart-loading-{card.id}", size="w-8 h-8",
                                           container_classes="min-h-[300px]"),
                    cls="w-full",
                    style="padding-top:20px; border-top:1px solid #1a2540;",
                ),

                style="background:#0d1424; border:1px solid #1a2540; border-radius:12px; padding:24px; max-width:56rem; width:100%; margin:0 1rem; position:relative;",
                onclick="event.stopPropagation();"
            ),
            cls="modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-center justify-center overflow-y-auto py-4",
            style="z-index: 10000;",
            onclick="window.closeCardModal();",
            data_card_id=card.id
        ),

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

            .card-version-nav:hover {
                background: rgba(255, 255, 255, 0.1);
                transition: background 0.2s ease;
                z-index: 30;
            }
            .card-version-nav:first-of-type:hover::after {
                content: '◀';
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                color: white; font-size: 1.5rem;
                text-shadow: 0 0 4px rgba(0,0,0,0.8);
                pointer-events: none; z-index: 31;
            }
            .card-version-nav:last-of-type:hover::after {
                content: '▶';
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                color: white; font-size: 1.5rem;
                text-shadow: 0 0 4px rgba(0,0,0,0.8);
                pointer-events: none; z-index: 31;
            }

            .card-nav-left:hover  { background: linear-gradient(to right, rgba(0,0,0,0.4), transparent); transition: background 0.2s ease; }
            .card-nav-right:hover { background: linear-gradient(to left,  rgba(0,0,0,0.4), transparent); transition: background 0.2s ease; }

            @media (min-width: 769px) {
                .card-nav-left, .card-nav-right { width: 64px; background: transparent; }
                .md\\:w-1\\/2:hover ~ .card-nav-left,
                .md\\:w-1\\/2:hover ~ .card-nav-right { pointer-events: none; opacity: 0.3; }
            }

            /* Progress bar (popularity) */
            .cm-progress-container {
                height: 16px;
                background: #080e1c;
                border: 1px solid #1a2540;
                border-radius: 8px;
                overflow: hidden;
            }
            .cm-progress-bar {
                height: 100%;
                background: linear-gradient(90deg, #0ea5e9, #38bdf8);
                display: flex;
                align-items: center;
                justify-content: flex-end;
                padding-right: 4px;
                transition: width 0.3s ease;
                border-radius: 8px;
            }

            /* Toggle switch */
            .toggle-track {
                width: 40px;
                height: 22px;
                background: #1a2540;
                border-radius: 11px;
                position: relative;
                transition: background 0.2s ease;
            }
            .toggle-thumb {
                width: 18px; height: 18px;
                background: #475569;
                border-radius: 50%;
                position: absolute;
                top: 2px; left: 2px;
                transition: transform 0.2s ease, background 0.2s ease;
            }
            input[type="checkbox"]:checked + .toggle-track { background: #0369a1; }
            input[type="checkbox"]:checked + .toggle-track .toggle-thumb {
                transform: translateX(18px);
                background: #38bdf8;
            }

            /* Mobile */
            @media (max-width: 768px) {
                .modal-backdrop { align-items: flex-start !important; padding: 1rem 0; }
                .modal-backdrop > div {
                    margin: 0 1rem;
                    max-height: none;
                    min-height: calc(100vh - 2rem);
                    width: calc(100% - 2rem);
                }
                .modal-backdrop > div > div:first-of-type { flex-direction: column; }
                .modal-backdrop > div > div:first-of-type .md\\:w-1\\/2 { width: 100%; }

                .mobile-close-btn {
                    top: 0.5rem !important; right: 0.5rem !important;
                    background: rgba(8,14,28,0.95) !important;
                    border: 1px solid #1a2540 !important;
                    box-shadow: 0 2px 8px rgba(0,0,0,0.4) !important;
                    z-index: 40 !important;
                }
                .mobile-watchlist-btn {
                    top: 0.5rem !important; right: 3rem !important;
                }

                .card-nav-left, .card-nav-right { width: 80px; }
                .card-nav-left:active  { background: linear-gradient(to right, rgba(0,0,0,0.6), transparent); }
                .card-nav-right:active { background: linear-gradient(to left,  rgba(0,0,0,0.6), transparent); }
                .card-nav-left::before {
                    content: '◀'; position: absolute; top: 50%; left: 50%;
                    transform: translate(-50%,-50%);
                    color: rgba(255,255,255,0.3); font-size: 1.5rem; font-weight: bold;
                    text-shadow: 0 0 8px rgba(0,0,0,0.9); pointer-events: none;
                }
                .card-nav-right::before {
                    content: '▶'; position: absolute; top: 50%; left: 50%;
                    transform: translate(-50%,-50%);
                    color: rgba(255,255,255,0.3); font-size: 1.5rem; font-weight: bold;
                    text-shadow: 0 0 8px rgba(0,0,0,0.9); pointer-events: none;
                }
            }

            @media (min-width: 769px) {
                .modal-backdrop { align-items: center; justify-content: center; }
                .modal-backdrop > div { max-height: 90vh; overflow-y: auto; }
            }

            /* Alt-art hint */
            .aa-hint-side {
                position: absolute; top: 0; bottom: 0; width: 36%;
                z-index: 29; pointer-events: none;
                display: flex; align-items: center; justify-content: center;
            }
            .aa-hint-left-side  { left: 0;  background: linear-gradient(to right, rgba(0,0,0,0.45), transparent); }
            .aa-hint-right-side { right: 0; background: linear-gradient(to left,  rgba(0,0,0,0.45), transparent); }
            .aa-hint-arrow {
                font-size: 2.5rem; color: white;
                text-shadow: 0 0 16px rgba(0,0,0,1), 0 0 32px rgba(255,255,255,0.3);
                animation: aa-pulse 0.65s ease-in-out infinite alternate;
            }
            .aa-hint-label {
                padding: 10px 18px; border-radius: 10px;
                background: rgba(0,0,0,0.88);
                border: 1px solid rgba(255,255,255,0.25);
                box-shadow: 0 4px 24px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.06);
                animation: aa-label-pulse 1.1s ease-in-out infinite alternate;
                white-space: nowrap;
            }
            @keyframes aa-pulse {
                from { transform: scale(1);   opacity: 0.75; }
                to   { transform: scale(1.3); opacity: 1; }
            }
            @keyframes aa-label-pulse {
                from { box-shadow: 0 4px 24px rgba(0,0,0,0.7), 0 0 0 1px rgba(255,255,255,0.06); }
                to   { box-shadow: 0 4px 24px rgba(0,0,0,0.7), 0 0 12px 2px rgba(255,255,255,0.18); }
            }

            canvas { max-width: 100% !important; height: auto !important; }
        """)
    )
