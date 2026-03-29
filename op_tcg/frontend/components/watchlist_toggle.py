from fasthtml import ft

def create_watchlist_toggle(card_id: str, card_version: int = 0, language: str = "en", is_in_watchlist: bool = False, extra_cls: str = "", btn_cls: str = "", include_script: bool = False) -> ft.Div:
    """
    Creates a heart icon button to toggle watchlist status.

    Args:
        card_id: The ID of the card
        card_version: The version (0 for base, >0 for alt art)
        language: Language code
        is_in_watchlist: Initial state
        extra_cls: Additional CSS classes for the button container
        btn_cls: CSS classes for the button itself (overrides default somewhat)
        include_script: Whether to include the global JS handler script (should only be done once per page generally, or handle re-definition safely)
    """

    # Unique ID for this button to update its state
    # We use a deterministic ID so we can find it easily if needed, but the button content update is handled via `this` in JS usually.
    # Actually, simpler to pass data attributes.

    icon_svg = '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>'

    default_btn_cls = "inline-flex items-center justify-center rounded-full p-2 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-400"

    # State-dependent classes
    state_cls = "text-red-500 bg-gray-800 hover:bg-gray-700" if is_in_watchlist else "text-gray-400 bg-gray-800 hover:text-red-400 hover:bg-gray-700"

    merged_cls = f"{default_btn_cls} {state_cls} {btn_cls}"

    script = None
    if include_script:
        script = ft.Script("""
            (function() {
                if (window.toggleWatchlistItem) return; // Already defined
                
                window.toggleWatchlistItem = async function(btn) {
                    const cardId = btn.dataset.cardId;
                    const cardVersion = btn.dataset.cardVersion;
                    const language = btn.dataset.language;
                    const isInWatchlist = btn.dataset.inWatchlist === 'true';
                    
                    const endpoint = isInWatchlist ? '/api/watchlist/remove' : '/api/watchlist/add';
                    
                    // Optimistic update
                    updateButtonState(btn, !isInWatchlist);
                    
                    try {
                        const response = await fetch(endpoint, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify({
                                card_id: cardId,
                                card_version: parseInt(cardVersion) || 0,
                                language: language || 'en'
                            })
                        });
                        
                        if (response.ok) {
                            // Confirm state
                            btn.dataset.inWatchlist = (!isInWatchlist).toString();
                            // If we are on the watchlist page and removed an item, maybe we want to hide the card?
                            // Check for a callback or event
                            if (isInWatchlist && window.location.pathname.includes('/watchlist')) {
                                // Find parent container to remove or fade out
                                const cardContainer = btn.closest('.watchlist-card-item');
                                if (cardContainer) {
                                    cardContainer.style.transition = 'opacity 0.5s';
                                    cardContainer.style.opacity = '0';
                                    setTimeout(() => cardContainer.remove(), 500);
                                }
                            }
                        } else {
                            // Revert
                            updateButtonState(btn, isInWatchlist);
                            if (response.status === 401) {
                                // Show generic login info modal
                                fetch('/api/info-modal?title=Login+Required&message=Please+login+to+manage+your+watchlist.&type=info&login=true')
                                    .then(r => r.text())
                                    .then(html => {
                                        document.body.insertAdjacentHTML('beforeend', html);
                                    });
                            }
                        }
                    } catch (e) {
                        console.error('Watchlist toggle failed', e);
                        updateButtonState(btn, isInWatchlist);
                    }
                };
                
                function updateButtonState(btn, inWatchlist) {
                    const svg = btn.querySelector('svg');
                    // Update dataset
                    btn.dataset.inWatchlist = inWatchlist.toString();
                    
                    if (inWatchlist) {
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
            })();
        """)

    button = ft.Button(
        ft.Svg(
            ft.Safe(icon_svg),
            viewBox="0 0 24 24",
            cls="w-6 h-6",
            fill="currentColor" if is_in_watchlist else "none",
            stroke="currentColor",
            stroke_width="2",
            stroke_linecap="round",
            stroke_linejoin="round"
        ),
        type="button",
        cls=merged_cls,
        onclick="window.toggleWatchlistItem(this); event.stopPropagation();",
        title="Remove from Watchlist" if is_in_watchlist else "Add to Watchlist",
        data_card_id=card_id,
        data_card_version=card_version,
        data_language=language,
        data_in_watchlist="true" if is_in_watchlist else "false"
    )

    if script:
        return ft.Div(script, button, cls=extra_cls)
    return ft.Div(button, cls=extra_cls)

