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

                window.toggleWatchlistItem = function(btn) {
                    const isInWatchlist = btn.dataset.inWatchlist === 'true';
                    if (isInWatchlist) {
                        performWatchlistAction(btn, true, null);
                    } else {
                        showTagPopover(btn);
                    }
                };

                async function performWatchlistAction(btn, isInWatchlist, tags) {
                    const cardId = btn.dataset.cardId;
                    const cardVersion = btn.dataset.cardVersion;
                    const language = btn.dataset.language;
                    const endpoint = isInWatchlist ? '/api/watchlist/remove' : '/api/watchlist/add';

                    updateButtonState(btn, !isInWatchlist);

                    try {
                        const body = {
                            card_id: cardId,
                            card_version: parseInt(cardVersion) || 0,
                            language: language || 'en'
                        };
                        if (tags && tags.length) body.tags = tags;

                        const response = await fetch(endpoint, {
                            method: 'POST',
                            headers: {'Content-Type': 'application/json'},
                            body: JSON.stringify(body)
                        });

                        if (response.ok) {
                            btn.dataset.inWatchlist = (!isInWatchlist).toString();
                            if (isInWatchlist && window.location.pathname.includes('/watchlist')) {
                                const cardContainer = btn.closest('.watchlist-card-item');
                                if (cardContainer) {
                                    cardContainer.style.transition = 'opacity 0.5s';
                                    cardContainer.style.opacity = '0';
                                    setTimeout(() => cardContainer.remove(), 500);
                                }
                            }
                        } else {
                            updateButtonState(btn, isInWatchlist);
                            if (response.status === 401) {
                                fetch('/api/info-modal?title=Login+Required&message=Please+login+to+manage+your+watchlist.&type=info&login=true')
                                    .then(r => r.text())
                                    .then(html => { document.body.insertAdjacentHTML('beforeend', html); });
                            }
                        }
                    } catch (e) {
                        console.error('Watchlist toggle failed', e);
                        updateButtonState(btn, isInWatchlist);
                    }
                }

                function updateButtonState(btn, inWatchlist) {
                    const svg = btn.querySelector('svg');
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

                function showTagPopover(btn) {
                    closeTagPopover();
                    const popover = document.createElement('div');
                    popover.id = 'watchlist-tag-popover';
                    popover.style.cssText = 'position:fixed;z-index:9999;background:#1f2937;border:1px solid #374151;border-radius:8px;padding:14px;box-shadow:0 10px 25px rgba(0,0,0,0.6);min-width:240px;';

                    const rect = btn.getBoundingClientRect();
                    const top = Math.min(rect.bottom + 8, window.innerHeight - 130);
                    const left = Math.max(Math.min(rect.left - 80, window.innerWidth - 260), 8);
                    popover.style.top = top + 'px';
                    popover.style.left = left + 'px';

                    popover.innerHTML = `
                        <div style="font-size:12px;color:#9ca3af;margin-bottom:6px;">Add to collection — tags (comma-separated)</div>
                        <input type="text" id="watchlist-tag-input" value="my collection"
                               style="width:100%;background:#374151;border:1px solid #4b5563;border-radius:4px;padding:5px 8px;color:#fff;font-size:13px;margin-bottom:8px;box-sizing:border-box;"
                               onkeydown="event.stopPropagation();if(event.key==='Enter'){event.preventDefault();window._confirmWatchlistTags();}"
                               onkeyup="event.stopPropagation();"
                               onkeypress="event.stopPropagation();" />
                        <div style="display:flex;gap:6px;">
                            <button onclick="window._confirmWatchlistTags()"
                                    style="flex:1;background:#2563eb;color:#fff;border:none;border-radius:4px;padding:5px 10px;font-size:13px;cursor:pointer;font-weight:500;">
                                Add
                            </button>
                            <button onclick="window.closeTagPopover()"
                                    style="background:#374151;color:#9ca3af;border:none;border-radius:4px;padding:5px 10px;font-size:13px;cursor:pointer;">
                                Cancel
                            </button>
                        </div>`;

                    popover._triggerBtn = btn;
                    document.body.appendChild(popover);
                    setTimeout(() => {
                        const input = document.getElementById('watchlist-tag-input');
                        if (input) { input.focus(); input.select(); }
                    }, 30);

                    setTimeout(() => {
                        document.addEventListener('click', function outsideClick(e) {
                            const p = document.getElementById('watchlist-tag-popover');
                            if (p && !p.contains(e.target) && e.target !== btn) {
                                closeTagPopover();
                                document.removeEventListener('click', outsideClick);
                            }
                        });
                    }, 100);
                }

                window.closeTagPopover = function() {
                    const p = document.getElementById('watchlist-tag-popover');
                    if (p) p.remove();
                };

                window._confirmWatchlistTags = function() {
                    const p = document.getElementById('watchlist-tag-popover');
                    if (!p) return;
                    const input = document.getElementById('watchlist-tag-input');
                    const raw = input ? input.value : 'my collection';
                    const tags = raw.split(',').map(t => t.trim()).filter(t => t.length > 0);
                    const btn = p._triggerBtn;
                    closeTagPopover();
                    if (btn) performWatchlistAction(btn, false, tags.length ? tags : ['my collection']);
                };
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

