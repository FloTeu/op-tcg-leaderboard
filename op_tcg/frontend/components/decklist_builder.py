"""
Reusable decklist builder component.

The JavaScript logic lives in public/js/decklist_builder.js (loaded once at
page startup). This component only emits a tiny inline prefill script so HTMX
never has to re-execute the large IIFE inside swapped content.
"""
import json
from fasthtml import ft
from op_tcg.backend.db import get_decklist_watchlist, get_custom_decklists
from op_tcg.backend.models.cards import OPTcgCardCatagory


def create_decklist_builder(
    user_id: str,
    card_lookup: dict,
    *,
    custom_id: str = "",
    prefill_name: str = "",
    prefill_leader_id: str = "",
    prefill_leader_img: str = "",
    prefill_leader_name: str = "",
    prefill_decklist: dict | None = None,
) -> ft.Div:
    """
    Return the full builder HTML fragment (id='decklist-builder-wrapper').

    The caller is responsible for resolving prefill data from import params
    before passing it in. The JS logic is in decklist_builder.js.
    """
    if prefill_decklist is None:
        prefill_decklist = {}

    # ── Build card-keyed prefill dict ──────────────────────────────────────
    prefill_cards: dict = {}
    for card_id, count in prefill_decklist.items():
        c = card_lookup.get(card_id)
        prefill_cards[card_id] = {
            'count': int(count),
            'name': c.name if c else card_id,
            'img': c.image_url if c else '',
            'is_leader': (c.card_category == OPTcgCardCatagory.LEADER) if c else False,
        }

    # ── Leader select options (all leaders sorted newest-set-first then name) ──
    leaders_sorted = sorted(
        [c for c in card_lookup.values() if c.card_category == OPTcgCardCatagory.LEADER],
        key=lambda c: (c.meta_format or '', c.name),
        reverse=True,
    )
    leader_select_options = [ft.Option("— select a leader —", value="", disabled=True, selected=not prefill_leader_id)]
    for lc in leaders_sorted:
        leader_select_options.append(ft.Option(
            f"{lc.name} ({lc.id})",
            value=lc.id,
            selected=(lc.id == prefill_leader_id),
            data_leader_name=lc.name,
            data_leader_img=lc.image_url,
        ))

    # ── Import-source dropdown options ─────────────────────────────────────
    dl_watchlist = get_decklist_watchlist(user_id)
    custom_decklists_list = get_custom_decklists(user_id)

    import_options = [ft.Option("— import from watchlist —", value="", selected=True, disabled=True)]

    if dl_watchlist:
        import_options.append(ft.Option("── Tournament Decklists ──", value="", disabled=True))
        for item in dl_watchlist:
            lid = item.get('leader_id', '')
            lname = card_lookup[lid].name if lid in card_lookup else lid
            tid = item.get('tournament_id', '')
            pid = item.get('player_id', '')
            import_url = (
                f"/api/watchlist/custom-decklist/builder"
                f"?import_tournament_id={tid}&import_player_id={pid}"
                + (f"&custom_id={custom_id}" if custom_id else "")
            )
            import_options.append(ft.Option(
                f"{lname} — {tid[:30]}",
                value=f"t:{tid}:{pid}",
                data_import_url=import_url,
            ))

    if custom_decklists_list:
        import_options.append(ft.Option("── Custom Decklists ──", value="", disabled=True))
        for d in custom_decklists_list:
            if d.get('id') == custom_id:
                continue  # skip self when editing
            import_url = (
                f"/api/watchlist/custom-decklist/builder"
                f"?import_custom_id={d['id']}"
                + (f"&custom_id={custom_id}" if custom_id else "")
            )
            import_options.append(ft.Option(
                d.get('name', 'Unnamed'),
                value=f"c:{d['id']}",
                data_import_url=import_url,
            ))

    # ── Tiny prefill script (all logic is in decklist_builder.js) ──────────
    prefill_data = {
        'cards': prefill_cards,
        'leaderId': prefill_leader_id,
        'leaderName': prefill_leader_name,
        'leaderImg': prefill_leader_img,
        'customId': custom_id or None,
    }
    prefill_js = (
        f"window._cdbInit = {json.dumps(prefill_data)};"
        " if (typeof window._cdbSetup === 'function') window._cdbSetup();"
    )

    close_js = (
        "var w = document.getElementById('decklist-builder-wrapper');"
        " if (w) { w.innerHTML = ''; w.classList.add('hidden'); }"
    )

    return ft.Div(
        ft.Script(prefill_js),
        # ── Header ───────────────────────────────────────────────────────
        ft.Div(
            ft.H2(
                "Custom Decklist Builder" if not custom_id else "Edit Decklist",
                cls="text-base font-bold text-white",
            ),
            ft.Button(
                ft.I(cls="fas fa-times"),
                type="button",
                cls="text-gray-400 hover:text-white transition-colors ml-auto",
                onclick=close_js,
            ),
            cls="flex items-center gap-3 mb-4",
        ),
        # ── Name + Import row ─────────────────────────────────────────────
        ft.Div(
            ft.Div(
                ft.Label("Name", cls="text-xs text-gray-400 block mb-1"),
                ft.Input(
                    type="text", id="cdb-name", value=prefill_name,
                    placeholder="My awesome deck...",
                    cls="w-full bg-gray-700 text-white border border-gray-600 rounded"
                        " px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500",
                ),
                cls="flex-1",
            ),
            ft.Div(
                ft.Label("Import from", cls="text-xs text-gray-400 block mb-1"),
                ft.Select(
                    *import_options,
                    id="cdb-import-select",
                    cls="w-full bg-gray-700 text-white border border-gray-600 rounded"
                        " px-2 py-1.5 text-sm focus:outline-none",
                    onchange="window._cdbImportChange(this)",
                ),
                cls="flex-1",
            ),
            cls="flex gap-3 mb-4 flex-col sm:flex-row",
        ),
        # ── Leader select + display ───────────────────────────────────────
        ft.Div(
            ft.Label("Leader", cls="text-xs text-gray-400 block mb-1"),
            ft.Select(
                *leader_select_options,
                id="cdb-leader-select",
                cls="w-full bg-gray-700 text-white border border-gray-600 rounded"
                    " px-2 py-1.5 text-sm focus:outline-none styled-select",
                onchange="window._cdbLeaderChange(this)",
            ),
            ft.Div(
                id="cdb-leader-display",
                cls="flex items-center gap-2 p-2 bg-gray-700/50 rounded border border-gray-600 min-h-[40px] mt-2",
            ),
            cls="mb-4",
        ),
        # ── Card search ───────────────────────────────────────────────────
        ft.Div(
            ft.Label("Search Cards", cls="text-xs text-gray-400 block mb-1"),
            ft.Input(
                type="text", name="search_term", id="cdb-search",
                placeholder="Search by name, meta format, type... (e.g. 'OP09 Luffy')",
                cls="w-full bg-gray-700 text-white border border-gray-600 rounded"
                    " px-3 py-1.5 text-sm focus:outline-none focus:border-blue-500 mb-2",
                hx_get="/api/decklist-builder/card-search",
                hx_trigger="keyup changed delay:400ms",
                hx_target="#cdb-search-results",
                hx_swap="innerHTML",
                hx_include="#cdb-search",
            ),
            ft.Div(
                ft.P("Type to search for cards.", cls="text-gray-500 text-sm text-center py-4"),
                id="cdb-search-results",
                cls="max-h-96 lg:max-h-[520px] overflow-y-auto",
            ),
            cls="mb-4",
        ),
        # ── Decklist panel ────────────────────────────────────────────────
        ft.Div(
            ft.Div(
                ft.Span("My Decklist", cls="text-xs text-gray-400 font-medium"),
                ft.Span("0 cards", id="cdb-deck-count", cls="text-xs text-gray-500 ml-2"),
                cls="flex items-center mb-2",
            ),
            ft.Div(
                ft.P("No cards yet.", cls="text-gray-500 text-sm text-center py-2"),
                id="cdb-decklist-panel",
                cls="max-h-48 overflow-y-auto",
            ),
            ft.Input(type="hidden", id="cdb-decklist-json", value="{}"),
            cls="mb-4 p-3 bg-gray-700/30 rounded border border-gray-600/50",
        ),
        # ── Footer ───────────────────────────────────────────────────────
        ft.Div(
            ft.Button(
                "Cancel",
                type="button",
                cls="px-4 py-2 text-sm text-gray-400 hover:text-white transition-colors",
                onclick=close_js,
            ),
            ft.Button(
                ft.I(cls="fas fa-save mr-2"),
                "Save Decklist",
                id="cdb-save-btn",
                type="button",
                cls="px-4 py-2 text-sm bg-blue-600 hover:bg-blue-500 text-white rounded"
                    " transition-colors font-medium inline-flex items-center",
                onclick="if (window._cdb) window._cdb.save();",
            ),
            cls="flex justify-end gap-3",
        ),
        id="decklist-builder-wrapper",
        cls="bg-gray-900 border border-gray-700 rounded-xl p-4 mb-6",
    )
