import json
import math
from fasthtml import ft
from fasthtml.common import NotStr
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup, get_all_tournament_decklist_data
from op_tcg.backend.models.cards import OPTcgCardCatagory
from op_tcg.backend.db import get_custom_decklists, get_decklist_watchlist

_CIRC = round(2 * math.pi * 36, 2)

_COLOR_DEFS = [
    ("Red",    "red",    "#ef4444", "Red"),
    ("Green",  "green",  "#22c55e", "Green"),
    ("Blue",   "blue",   "#3b82f6", "Blue"),
    ("Purple", "purple", "#a855f7", "Purple"),
    ("Black",  "black",  "#9ca3af", "Black"),
    ("Yellow", "yellow", "#eab308", "Yellow"),
]


def _styles() -> ft.Style:
    return ft.Style("""
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.db-display { font-family: 'Bebas Neue', sans-serif; letter-spacing: 0.06em; }
.db-mono    { font-family: 'Share Tech Mono', monospace; }
.db-body    { font-family: 'Barlow', sans-serif; }

.db-page { background: #070b14; font-family: 'Barlow', sans-serif; }

.db-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
}

.db-panel-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.12em;
    color: #334155;
    font-size: 0.65rem;
    text-transform: uppercase;
    margin-bottom: 8px;
}

.db-leader-frame {
    background: #080e1c;
    border: 1.5px solid #1a2540;
    border-radius: 8px;
    min-height: 72px;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: border-color 0.3s, box-shadow 0.3s;
    padding: 10px;
}
.db-leader-frame.has-leader {
    border-color: rgba(245,158,11,0.6);
    box-shadow: 0 0 24px rgba(245,158,11,0.12);
}

.db-filter-chip {
    display: inline-flex;
    align-items: center;
    padding: 3px 10px;
    border-radius: 20px;
    font-size: 0.7rem;
    font-weight: 500;
    background: #0d1424;
    color: #475569;
    border: 1px solid #1a2540;
    cursor: pointer;
    transition: all 0.12s;
    user-select: none;
    white-space: nowrap;
}
.db-filter-chip:hover { border-color: #2d3f5a; color: #64748b; }
.db-filter-chip.active {
    background: rgba(245,158,11,0.12);
    color: #f59e0b;
    border-color: rgba(245,158,11,0.35);
}
.db-chip-cat.active {
    background: rgba(56,189,248,0.1);
    color: #38bdf8;
    border-color: rgba(56,189,248,0.3);
}
.db-chip-color-red.active    { background:rgba(239,68,68,.12); color:#ef4444; border-color:rgba(239,68,68,.35); }
.db-chip-color-green.active  { background:rgba(34,197,94,.12); color:#22c55e; border-color:rgba(34,197,94,.35); }
.db-chip-color-blue.active   { background:rgba(59,130,246,.12); color:#60a5fa; border-color:rgba(59,130,246,.35); }
.db-chip-color-purple.active { background:rgba(168,85,247,.12); color:#c084fc; border-color:rgba(168,85,247,.35); }
.db-chip-color-black.active  { background:rgba(148,163,184,.12); color:#cbd5e1; border-color:rgba(148,163,184,.35); }
.db-chip-color-yellow.active { background:rgba(234,179,8,.12); color:#facc15; border-color:rgba(234,179,8,.35); }

.db-search {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 10px 14px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.875rem;
    outline: none;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.db-search:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }
.db-search::placeholder { color: #1e2d45; }

.db-leader-select {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 8px 10px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.8rem;
    outline: none;
    cursor: pointer;
    transition: border-color 0.15s;
}
.db-leader-select:focus { border-color: #f59e0b; }

.db-name-input {
    background: transparent;
    border: none;
    border-bottom: 1.5px solid #1a2540;
    color: #f1f5f9;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1.6rem;
    letter-spacing: 0.05em;
    padding: 2px 0 4px;
    outline: none;
    width: 100%;
    transition: border-color 0.15s;
    min-width: 0;
}
.db-name-input:focus { border-bottom-color: #f59e0b; }
.db-name-input::placeholder { color: #1a2540; }

.db-btn-primary {
    background: #f59e0b;
    color: #000;
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    font-size: 1rem;
    padding: 7px 22px;
    border-radius: 8px;
    border: none;
    cursor: pointer;
    transition: background 0.12s, transform 0.1s;
    white-space: nowrap;
}
.db-btn-primary:hover { background: #fbbf24; transform: translateY(-1px); }
.db-btn-primary:disabled { background: #1a2540; color: #334155; transform: none; cursor: not-allowed; }

.db-btn-ghost {
    background: transparent;
    color: #475569;
    font-family: 'Barlow', sans-serif;
    font-size: 0.78rem;
    font-weight: 500;
    padding: 6px 12px;
    border-radius: 6px;
    border: 1px solid #1a2540;
    cursor: pointer;
    transition: all 0.12s;
    white-space: nowrap;
}
.db-btn-ghost:hover { color: #94a3b8; border-color: #2d3f5a; background: #0d1424; }

.db-deck-row {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 5px 0;
    border-bottom: 1px solid #111d30;
}
.db-deck-row:last-child { border-bottom: none; }

.db-qty-btn {
    width: 20px; height: 20px;
    background: #111d30;
    border: none; border-radius: 4px;
    color: #64748b; cursor: pointer;
    display: flex; align-items: center; justify-content: center;
    font-size: 0.75rem;
    transition: background 0.12s, color 0.12s;
    flex-shrink: 0;
}
.db-qty-btn:hover { background: #1e2d45; color: #f1f5f9; }

.db-progress-ring { transition: stroke-dashoffset 0.4s cubic-bezier(.4,0,.2,1), stroke 0.3s; }

.db-cost-bar-wrap {
    display: flex;
    align-items: flex-end;
    gap: 3px;
    height: 36px;
}
.db-cost-bar {
    flex: 1;
    background: rgba(245,158,11,0.55);
    border-radius: 2px 2px 0 0;
    min-height: 2px;
    transition: height 0.25s ease;
}

.db-tab-btn {
    flex: 1; padding: 10px 4px;
    background: transparent; border: none;
    color: #334155;
    font-family: 'Bebas Neue', sans-serif;
    font-size: 1rem; letter-spacing: 0.1em;
    cursor: pointer;
    border-bottom: 2px solid transparent;
    transition: all 0.12s;
}
.db-tab-btn.active-tab { color: #f59e0b; border-bottom-color: #f59e0b; }

.db-card-grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px; }
@media (min-width: 640px) { .db-card-grid { grid-template-columns: repeat(4, 1fr); } }
@media (min-width: 1024px) { .db-card-grid { grid-template-columns: repeat(3, 1fr); } }
@media (min-width: 1280px) { .db-card-grid { grid-template-columns: repeat(4, 1fr); } }

.db-three-col { display: flex; flex-direction: column; gap: 1rem; }
@media (min-width: 1280px) {
    .db-three-col { display: grid; grid-template-columns: 260px 1fr 300px; gap: 1rem; }
    .db-xl-show { display: block !important; }
}

.db-card-item {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 6px;
    overflow: hidden;
    transition: border-color 0.12s, transform 0.12s;
    cursor: pointer;
}
.db-card-item:hover { border-color: #38bdf8; transform: translateY(-2px); }

.db-scroll::-webkit-scrollbar { width: 3px; }
.db-scroll::-webkit-scrollbar-track { background: transparent; }
.db-scroll::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 2px; }

@keyframes dbFadeIn { from { opacity:0; transform:scale(.96) translateY(3px); } to { opacity:1; transform:none; } }
#cdb-search-results .db-card-item { animation: dbFadeIn 0.18s ease; }

/* Sticky panels on desktop */
@media (min-width: 1280px) {
    .db-panel-sticky { position: sticky; top: 16px; max-height: calc(100vh - 140px); overflow-y: auto; }
    .db-panel-sticky.db-scroll::-webkit-scrollbar { width: 3px; }
}
""")


def _page_script(prefill_data: dict) -> ft.Script:
    # Tiny init script — all logic lives in public/js/deckbuilder.js
    init_json = json.dumps(prefill_data)
    return ft.Script(f"""
window._cdbInit = {init_json};
if (typeof window._dbSetup === 'function') {{
  window._dbSetup();
}} else {{
  document.addEventListener('DOMContentLoaded', function() {{
    if (typeof window._dbSetup === 'function') window._dbSetup();
  }});
}}
""")


def deckbuilder_page(request):
    user = request.session.get('user')
    if not user:
        return ft.Div(
            ft.H1("Access Denied", cls="db-display text-3xl text-white mb-4"),
            ft.P("Please log in to use the Deck Builder.", cls="text-gray-400 db-body"),
            ft.A("Log in", href="/login", cls="inline-block mt-4 db-btn-primary"),
            cls="db-page db-body min-h-screen flex flex-col items-center justify-center gap-2"
        )

    user_id = user.get('sub')
    card_lookup = get_card_id_card_data_lookup()
    custom_id = request.query_params.get('custom_id', '')
    import_tournament_id = request.query_params.get('import_tournament_id', '')
    import_player_id = request.query_params.get('import_player_id', '')
    import_custom_id = request.query_params.get('import_custom_id', '')

    # Resolve prefill (edit mode or import)
    prefill_name, prefill_leader_id, prefill_leader_img, prefill_leader_name, prefill_decklist = '', '', '', '', {}
    if custom_id:
        customs = get_custom_decklists(user_id)
        match = next((d for d in customs if d.get('id') == custom_id), None)
        if match:
            prefill_name = match.get('name', '')
            prefill_leader_id = match.get('leader_id', '')
            prefill_decklist = {k: int(v) for k, v in (match.get('decklist') or {}).items()}

    if import_tournament_id and import_player_id:
        td = next(
            (x for x in get_all_tournament_decklist_data()
             if x.tournament_id == import_tournament_id and x.player_id == import_player_id),
            None,
        )
        if td:
            prefill_decklist = {k: int(v) for k, v in (td.decklist or {}).items()}
            if not prefill_leader_id:
                prefill_leader_id = td.leader_id

    if import_custom_id:
        for d in get_custom_decklists(user_id):
            if d.get('id') == import_custom_id:
                prefill_decklist = {k: int(v) for k, v in (d.get('decklist') or {}).items()}
                if not prefill_leader_id:
                    prefill_leader_id = d.get('leader_id', '')
                break

    if prefill_leader_id in card_lookup:
        lc = card_lookup[prefill_leader_id]
        prefill_leader_img = lc.image_url
        prefill_leader_name = lc.name

    # Build prefill_cards for JS
    prefill_cards = {}
    for cid, count in prefill_decklist.items():
        c = card_lookup.get(cid)
        prefill_cards[cid] = {
            'count': int(count),
            'name': c.name if c else cid,
            'img': c.image_url if c else '',
            'is_leader': (c.card_category == OPTcgCardCatagory.LEADER) if c else False,
            'cost': int(c.cost or 0) if c and c.cost else 0,
            'type': c.card_category.value if c else '',
        }

    prefill_leader_colors = []
    if prefill_leader_id in card_lookup:
        prefill_leader_colors = [col.value for col in card_lookup[prefill_leader_id].colors]

    prefill_data = {
        'cards': prefill_cards,
        'leaderId': prefill_leader_id,
        'leaderName': prefill_leader_name,
        'leaderImg': prefill_leader_img,
        'leaderColors': prefill_leader_colors,
        'customId': custom_id or None,
    }

    # Leader dropdown options
    leaders_sorted = sorted(
        [c for c in card_lookup.values() if c.card_category == OPTcgCardCatagory.LEADER],
        key=lambda c: (c.meta_format or '', c.name), reverse=True,
    )
    leader_opts = [ft.Option("— select leader —", value="", disabled=True, selected=not prefill_leader_id)]
    for lc in leaders_sorted:
        leader_opts.append(ft.Option(
            f"{lc.name} ({lc.id})",
            value=lc.id,
            selected=(lc.id == prefill_leader_id),
            data_leader_name=lc.name,
            data_leader_img=lc.image_url,
            data_leader_colors=json.dumps([c.value for c in lc.colors]),
        ))

    # Import options
    dl_watchlist = get_decklist_watchlist(user_id)
    customs_all = get_custom_decklists(user_id)
    import_opts = [ft.Option("— import from —", value="", disabled=True, selected=True)]
    if dl_watchlist:
        import_opts.append(ft.Option("── Tournament Decklists ──", value="", disabled=True))
        for item in dl_watchlist:
            lid = item.get('leader_id', '')
            lname = card_lookup[lid].name if lid in card_lookup else lid
            tid = item.get('tournament_id', '')
            pid = item.get('player_id', '')
            url = f"/deckbuilder?import_tournament_id={tid}&import_player_id={pid}" + (f"&custom_id={custom_id}" if custom_id else "")
            import_opts.append(ft.Option(f"{lname} — {tid[:28]}", value=f"t:{tid}:{pid}", data_import_url=url))
    if customs_all:
        import_opts.append(ft.Option("── Custom Decklists ──", value="", disabled=True))
        for d in customs_all:
            if d.get('id') == custom_id:
                continue
            url = f"/deckbuilder?import_custom_id={d['id']}" + (f"&custom_id={custom_id}" if custom_id else "")
            import_opts.append(ft.Option(d.get('name', 'Unnamed'), value=f"c:{d['id']}", data_import_url=url))

    # ── Subcomponents ────────────────────────────────────────────────────────

    hx_include = "#cdb-search, #cdb-color-filters, #cdb-category-filters"

    # Left panel: leader + filters
    left_panel = ft.Div(
        # Leader select
        ft.Div(
            ft.Div("Leader", cls="db-panel-label"),
            ft.Select(
                *leader_opts,
                id="cdb-leader-select",
                cls="db-leader-select styled-select",
                onchange="window._cdbLeaderChange(this)",
            ),
            ft.Div(
                id="cdb-leader-display",
                cls="db-leader-frame mt-2",
            ),
            cls="mb-5",
        ),
        # Color filter chips
        ft.Div(
            ft.Div("Colors", cls="db-panel-label"),
            ft.Div(
                *[
                    ft.Button(
                        ft.Span(cls="w-2.5 h-2.5 rounded-full flex-shrink-0 mr-1.5",
                                style=f"background:{hex_col}"),
                        label,
                        type="button",
                        cls=f"db-filter-chip db-chip-color db-chip-color-{key}",
                        data_color=val,
                        onclick="window._dbToggleColor(this)",
                    )
                    for label, key, hex_col, val in _COLOR_DEFS
                ],
                cls="flex flex-wrap gap-1.5",
            ),
            ft.Div(id="cdb-color-filters"),
            cls="mb-5",
        ),
        # Type filter chips
        ft.Div(
            ft.Div("Type", cls="db-panel-label"),
            ft.Div(
                *[
                    ft.Button(
                        cat.value,
                        type="button",
                        cls="db-filter-chip db-chip-cat",
                        data_cat=cat.value,
                        onclick="window._dbToggleCat(this)",
                    )
                    for cat in [OPTcgCardCatagory.CHARACTER, OPTcgCardCatagory.EVENT, OPTcgCardCatagory.STAGE]
                ],
                cls="flex flex-wrap gap-1.5",
            ),
            ft.Div(id="cdb-category-filters"),
            cls="mb-5",
        ),
        # Import
        ft.Div(
            ft.Div("Import", cls="db-panel-label"),
            ft.Select(
                *import_opts,
                id="cdb-import-select",
                cls="db-leader-select mb-2",
                onchange="window._cdbImportChange(this)",
            ),
            ft.Button(
                ft.I(cls="fas fa-clipboard mr-1.5 text-xs"),
                "Paste from clipboard",
                type="button",
                cls="db-btn-ghost w-full flex items-center justify-center text-xs",
                onclick="window._cdbPasteImport()",
            ),
            cls="mb-2",
        ),
        cls="db-panel db-panel-sticky db-scroll p-4",
    )

    # Center panel: card browser
    center_panel = ft.Div(
        ft.Input(
            type="text", name="search_term", id="cdb-search",
            placeholder="Search cards by name, type, set… (e.g. OP09 Luffy)",
            cls="db-search mb-3",
            hx_get="/api/decklist-builder/card-search",
            hx_trigger="keyup changed delay:350ms",
            hx_target="#cdb-search-results",
            hx_swap="innerHTML",
            hx_include=hx_include,
        ),
        ft.Div(
            ft.P("Type to search for cards.", cls="text-center db-body",
                 style="color:#1e2d45;font-size:.8rem;padding:40px 0;"),
            id="cdb-search-results",
            cls="db-scroll overflow-y-auto",
            style="max-height: calc(100vh - 220px);",
        ),
        cls="db-panel p-4 flex flex-col",
        style="min-height: 400px;",
    )

    # Right panel: deck list
    right_panel = ft.Div(
        # Progress ring + type stats
        ft.Div(
            ft.Div(
                NotStr(
                    f'<svg viewBox="0 0 80 80" style="width:68px;height:68px;">'
                    f'<circle cx="40" cy="40" r="36" fill="none" stroke="#111d30" stroke-width="5"/>'
                    f'<circle id="db-ring" cx="40" cy="40" r="36" fill="none"'
                    f' stroke="#f59e0b" stroke-width="5"'
                    f' stroke-dasharray="{_CIRC}" stroke-dashoffset="{_CIRC}"'
                    f' stroke-linecap="round"'
                    f' class="db-progress-ring"'
                    f' style="transform:rotate(-90deg);transform-origin:50% 50%;"/>'
                    f'</svg>'
                ),
                ft.Div(
                    ft.Span("0", id="db-ring-num",
                            style="font-family:'Share Tech Mono',monospace;font-size:1.3rem;color:#f1f5f9;line-height:1;"),
                    ft.Span("/50",
                            style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#334155;"),
                    style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;",
                ),
                style="position:relative;width:68px;height:68px;flex-shrink:0;",
            ),
            ft.Div(
                *[
                    ft.Div(
                        ft.Span(cat, cls="db-panel-label mb-0"),
                        ft.Span("0", id=f"db-tc-{cat.lower()}",
                                style="font-family:'Share Tech Mono',monospace;font-size:.9rem;color:#475569;"),
                        cls="flex flex-col items-center",
                    )
                    for cat in ["Character", "Event", "Stage"]
                ],
                cls="flex gap-4 items-center",
            ),
            cls="flex items-center gap-4 mb-4",
        ),
        # Deck list
        ft.Div(
            ft.P("Add cards from the browser",
                 style="color:#1e2d45;font-family:Barlow,sans-serif;font-size:.8rem;text-align:center;padding:24px 0;"),
            id="cdb-decklist-panel",
            cls="db-scroll overflow-y-auto mb-4",
            style="max-height: calc(100vh - 440px); min-height: 120px;",
        ),
        ft.Input(type="hidden", id="cdb-decklist-json", value="{}"),
        # Cost curve
        ft.Div(
            ft.Div("Cost Curve", cls="db-panel-label"),
            ft.Div(
                *[
                    ft.Div(id=f"db-bar-{i}", cls="db-cost-bar",
                           title=f"Cost {i if i < 10 else '10+'}: 0",
                           style="height:2px;")
                    for i in range(11)
                ],
                cls="db-cost-bar-wrap",
            ),
            ft.Div(
                *[
                    ft.Span(str(i) if i < 10 else "10+",
                            style="flex:1;text-align:center;font-family:'Share Tech Mono',monospace;font-size:.55rem;color:#1e2d45;")
                    for i in range(11)
                ],
                style="display:flex;margin-top:2px;",
            ),
            cls="mb-4",
        ),
        cls="db-panel db-panel-sticky db-scroll p-4",
    )

    # ── Page header ──────────────────────────────────────────────────────────
    page_header = ft.Div(
        ft.Div(
            ft.A("← Watchlist", href="/watchlist?section=decklists",
                 style="font-family:Barlow,sans-serif;font-size:.72rem;color:#334155;text-decoration:none;transition:color .15s;"
                        " onmouseover=\"this.style.color='#64748b'\" onmouseout=\"this.style.color='#334155'\""),
            ft.H1(
                "Edit Deck" if custom_id else "Deck Builder",
                cls="db-display",
                style="font-size:2rem;color:#f1f5f9;margin:2px 0 0;line-height:1;",
            ),
        ),
        ft.Div(
            ft.Input(
                id="cdb-name", type="text",
                value=prefill_name,
                placeholder="NAME YOUR DECK",
                cls="db-name-input",
                style="max-width:320px;",
            ),
        ),
        ft.Div(
            ft.Button(
                ft.I(cls="fas fa-file-export mr-1.5 text-xs"),
                "Export",
                id="db-export-btn",
                type="button",
                cls="db-btn-ghost",
                onclick="window._dbExport()",
            ),
            ft.Button(
                ft.I(cls="fas fa-save mr-1.5 text-xs"),
                "SAVE DECK",
                id="cdb-save-btn",
                type="button",
                cls="db-btn-primary",
                onclick="if(window._cdb) window._cdb.save();",
            ),
            cls="flex items-center gap-2",
        ),
        cls="flex items-end justify-between gap-4 mb-4 flex-wrap",
        style="padding-bottom:12px;border-bottom:1px solid #111d30;",
    )

    # ── Mobile tabs ──────────────────────────────────────────────────────────
    mobile_tabs = ft.Div(
        ft.Button("Browse", id="db-tab-browse", type="button",
                  cls="db-tab-btn active-tab",
                  onclick="window._switchBuilderTab('browse')"),
        ft.Button("My Deck", id="db-tab-deck", type="button",
                  cls="db-tab-btn",
                  onclick="window._switchBuilderTab('deck')"),
        cls="flex xl:hidden border-b mb-4",
        style="border-color:#111d30;",
    )

    return ft.Div(
        _styles(),
        _page_script(prefill_data),
        ft.Div(
            page_header,
            mobile_tabs,
            # Three-panel grid
            ft.Div(
                # Left: hidden on mobile
                ft.Div(
                    left_panel,
                    cls="db-xl-show",
                    style="display:none;",
                ),
                # Center: card browser
                ft.Div(
                    # Mobile: show left panel filters as collapsible
                    ft.Details(
                        ft.Summary(
                            ft.I(cls="fas fa-sliders-h mr-2 text-xs"),
                            "Filters",
                            style="font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:.85rem;color:#475569;cursor:pointer;list-style:none;display:flex;align-items:center;padding:8px 12px;background:#0d1424;border:1px solid #1a2540;border-radius:6px;margin-bottom:10px;",
                        ),
                        ft.Div(
                            # Duplicate color + type chips for mobile (separate IDs)
                            ft.Div(
                                ft.Div("Colors", cls="db-panel-label"),
                                ft.Div(
                                    *[
                                        ft.Button(
                                            ft.Span(cls="w-2.5 h-2.5 rounded-full flex-shrink-0 mr-1",
                                                    style=f"background:{hex_col}"),
                                            label,
                                            type="button",
                                            cls=f"db-filter-chip db-chip-color db-chip-color-{key}",
                                            data_color=val,
                                            onclick="window._dbToggleColor(this)",
                                        )
                                        for label, key, hex_col, val in _COLOR_DEFS
                                    ],
                                    cls="flex flex-wrap gap-1.5",
                                ),
                                cls="mb-3",
                            ),
                            ft.Div(
                                ft.Div("Type", cls="db-panel-label"),
                                ft.Div(
                                    *[
                                        ft.Button(
                                            cat.value,
                                            type="button",
                                            cls="db-filter-chip db-chip-cat",
                                            data_cat=cat.value,
                                            onclick="window._dbToggleCat(this)",
                                        )
                                        for cat in [OPTcgCardCatagory.CHARACTER, OPTcgCardCatagory.EVENT, OPTcgCardCatagory.STAGE]
                                    ],
                                    cls="flex flex-wrap gap-1.5",
                                ),
                                cls="mb-3",
                            ),
                            cls="p-3 db-panel mb-3",
                        ),
                        cls="xl:hidden",
                    ),
                    center_panel,
                    id="db-browse-panel",
                ),
                # Right: deck panel (hidden on mobile, shown via tab or xl grid)
                ft.Div(
                    right_panel,
                    id="db-deck-panel",
                    cls="db-xl-show",
                    style="display:none;",
                ),
                cls="db-three-col",
            ),
            cls="db-page px-4 py-4 md:px-6",
        ),
        cls="db-page",
    )
