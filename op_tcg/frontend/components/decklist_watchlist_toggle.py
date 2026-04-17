from fasthtml import ft


def create_decklist_watchlist_toggle(
    leader_id: str,
    tournament_id: str,
    player_id: str,
    is_in_watchlist: bool = False,
    extra_cls: str = "",
    btn_cls: str = "",
    include_script: bool = False,
) -> ft.Div:
    """Heart icon button to toggle a tournament decklist in/out of the watchlist.

    Args:
        leader_id: Leader card ID for this decklist
        tournament_id: Tournament identifier
        player_id: Player identifier
        is_in_watchlist: Current watchlist state
        extra_cls: CSS classes for the outer wrapper div
        btn_cls: Additional CSS classes for the button itself
        include_script: Whether to embed the JS handler (once per page)
    """
    icon_svg = '<path d="M20.84 4.61a5.5 5.5 0 0 0-7.78 0L12 5.67l-1.06-1.06a5.5 5.5 0 0 0-7.78 7.78l1.06 1.06L12 21.23l7.78-7.78 1.06-1.06a5.5 5.5 0 0 0 0-7.78z"></path>'

    default_btn_cls = "inline-flex items-center justify-center rounded-full p-2 transition-colors focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-red-400"
    state_cls = "text-red-500 bg-gray-800 hover:bg-gray-700" if is_in_watchlist else "text-gray-400 bg-gray-800 hover:text-red-400 hover:bg-gray-700"
    merged_cls = f"{default_btn_cls} {state_cls} {btn_cls}"

    script = None
    if include_script:
        script = ft.Script("""
(function() {
    if (window.toggleDecklistWatchlistItem) return;

    window.toggleDecklistWatchlistItem = function(btn) {
        const isInWatchlist = btn.dataset.inWatchlist === 'true';
        if (isInWatchlist) {
            _performDecklistAction(btn, true, null);
        } else {
            _showDecklistTagPopover(btn);
        }
    };

    async function _performDecklistAction(btn, isInWatchlist, tags) {
        const leaderId = btn.dataset.leaderId;
        const tournamentId = btn.dataset.tournamentId;
        const playerId = btn.dataset.playerId;
        const endpoint = isInWatchlist ? '/api/watchlist/decklist/remove' : '/api/watchlist/decklist/add';

        _updateDecklistBtnState(btn, !isInWatchlist);

        try {
            const body = { leader_id: leaderId, tournament_id: tournamentId, player_id: playerId };
            if (tags && tags.length) body.tags = tags;

            const response = await fetch(endpoint, {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify(body)
            });

            if (response.ok) {
                btn.dataset.inWatchlist = (!isInWatchlist).toString();
                // Keep the modal's cached watchlist set in sync
                const backdrop = document.getElementById('decklist-modal-backdrop');
                if (backdrop) {
                    try {
                        const key = tournamentId + ':' + playerId;
                        let watchlisted = JSON.parse(backdrop.dataset.watchlistedDecklists || '[]');
                        if (!isInWatchlist) {
                            if (!watchlisted.includes(key)) watchlisted.push(key);
                        } else {
                            watchlisted = watchlisted.filter(k => k !== key);
                        }
                        backdrop.dataset.watchlistedDecklists = JSON.stringify(watchlisted);
                    } catch(e) {}
                }
                // Fade-out on watchlist page
                if (isInWatchlist && window.location.pathname.includes('/watchlist')) {
                    const item = btn.closest('.decklist-watchlist-item');
                    if (item) {
                        item.style.transition = 'opacity 0.5s';
                        item.style.opacity = '0';
                        setTimeout(() => item.remove(), 500);
                    }
                }
            } else {
                _updateDecklistBtnState(btn, isInWatchlist);
                if (response.status === 401) {
                    fetch('/api/info-modal?title=Login+Required&message=Please+login+to+manage+your+watchlist.&type=info&login=true')
                        .then(r => r.text())
                        .then(html => { document.body.insertAdjacentHTML('beforeend', html); });
                }
            }
        } catch(e) {
            console.error('Decklist watchlist toggle failed', e);
            _updateDecklistBtnState(btn, isInWatchlist);
        }
    }

    function _updateDecklistBtnState(btn, inWatchlist) {
        const svg = btn.querySelector('svg');
        btn.dataset.inWatchlist = inWatchlist.toString();
        if (inWatchlist) {
            svg.setAttribute('fill', 'currentColor');
            btn.classList.remove('text-gray-400', 'hover:text-red-400');
            btn.classList.add('text-red-500');
            btn.title = 'Remove from Watchlist';
        } else {
            svg.setAttribute('fill', 'none');
            btn.classList.add('text-gray-400', 'hover:text-red-400');
            btn.classList.remove('text-red-500');
            btn.title = 'Add to Watchlist';
        }
    }

    function _showDecklistTagPopover(btn) {
        const existing = document.getElementById('watchlist-tag-popover');
        if (existing) existing.remove();

        const popover = document.createElement('div');
        popover.id = 'watchlist-tag-popover';
        popover.style.cssText = 'position:fixed;z-index:10000;background:#1f2937;border:1px solid #374151;border-radius:8px;padding:14px;box-shadow:0 10px 25px rgba(0,0,0,0.6);min-width:240px;';

        const rect = btn.getBoundingClientRect();
        const top = Math.min(rect.bottom + 8, window.innerHeight - 130);
        const left = Math.max(Math.min(rect.left - 80, window.innerWidth - 260), 8);
        popover.style.top = top + 'px';
        popover.style.left = left + 'px';

        popover.innerHTML = `
            <div style="font-size:12px;color:#9ca3af;margin-bottom:6px;">Save decklist — tags (comma-separated)</div>
            <input type="text" id="watchlist-tag-input" value="my decklists"
                   style="width:100%;background:#374151;border:1px solid #4b5563;border-radius:4px;padding:5px 8px;color:#fff;font-size:13px;margin-bottom:8px;box-sizing:border-box;"
                   onkeydown="event.stopPropagation();if(event.key==='Enter'){event.preventDefault();window._confirmDecklistWatchlistTags();}"
                   onkeyup="event.stopPropagation();"
                   onkeypress="event.stopPropagation();" />
            <div style="display:flex;gap:6px;">
                <button onclick="window._confirmDecklistWatchlistTags()"
                        style="flex:1;background:#2563eb;color:#fff;border:none;border-radius:4px;padding:5px 10px;font-size:13px;cursor:pointer;font-weight:500;">
                    Save
                </button>
                <button onclick="document.getElementById('watchlist-tag-popover').remove()"
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
                    p.remove();
                    document.removeEventListener('click', outsideClick);
                }
            });
        }, 100);
    }

    window._confirmDecklistWatchlistTags = function() {
        const p = document.getElementById('watchlist-tag-popover');
        if (!p) return;
        const input = document.getElementById('watchlist-tag-input');
        const raw = input ? input.value : 'my decklists';
        const tags = raw.split(',').map(t => t.trim()).filter(t => t.length > 0);
        const btn = p._triggerBtn;
        p.remove();
        if (btn) _performDecklistAction(btn, false, tags.length ? tags : ['my decklists']);
    };

    // Sync the watchlist button in the decklist modal header when a new decklist is selected
    document.addEventListener('htmx:afterSwap', function(e) {
        if (!e.detail || !e.detail.target) return;
        if (e.detail.target.id !== 'selected-tournament-decklist-content-modal') return;
        const sel = document.getElementById('tournament-decklist-select-modal');
        if (!sel || !sel.value) return;
        const parts = sel.value.split(':');
        const tournamentId = parts[0];
        const playerId = parts.slice(1).join(':');
        const btn = document.getElementById('decklist-modal-watchlist-btn-el');
        if (!btn) return;
        const backdrop = document.getElementById('decklist-modal-backdrop');
        let watchlisted = [];
        try { watchlisted = JSON.parse(backdrop?.dataset?.watchlistedDecklists || '[]'); } catch(e) {}
        const key = tournamentId + ':' + playerId;
        const inWatchlist = watchlisted.includes(key);
        btn.dataset.tournamentId = tournamentId;
        btn.dataset.playerId = playerId;
        _updateDecklistBtnState(btn, inWatchlist);
    });
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
            stroke_linejoin="round",
        ),
        type="button",
        cls=merged_cls,
        id="decklist-modal-watchlist-btn-el",
        onclick="window.toggleDecklistWatchlistItem(this); event.stopPropagation();",
        title="Remove from Watchlist" if is_in_watchlist else "Add to Watchlist",
        data_leader_id=leader_id,
        data_tournament_id=tournament_id,
        data_player_id=player_id,
        data_in_watchlist="true" if is_in_watchlist else "false",
    )

    if script:
        return ft.Div(script, button, cls=extra_cls)
    return ft.Div(button, cls=extra_cls)
