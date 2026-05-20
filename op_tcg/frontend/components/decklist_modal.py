from fasthtml import ft
from op_tcg.backend.etl.extract import get_card_image_url
from op_tcg.backend.models.cards import ExtendedCardData, OPTcgLanguage, CardCurrency, OPTcgCardCatagory
from op_tcg.frontend.utils.decklist import DecklistViewMode
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.decklist_export import create_decklist_export_component
from op_tcg.frontend.components.decklist_watchlist_toggle import create_decklist_watchlist_toggle

_LABEL_STYLE = "font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.65rem; color:#334155; text-transform:uppercase; display:block; margin-bottom:6px;"
_STAT_LABEL = "font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.6rem; color:#475569; text-transform:uppercase; display:block; margin-top:4px;"
_STAT_VALUE = "font-family:'Share Tech Mono',monospace; font-size:1.4rem; line-height:1; display:block;"
_PANEL_STYLE = "background:#0d1424; border:1px solid #1a2540; border-radius:8px; padding:14px;"


def display_decklist_list_view(decklist: dict[str, int], card_id2card_data: dict[str, ExtendedCardData],
                                leader_id: str = None, currency: str = CardCurrency.EURO,
                                unique_id: str = "default"):
    """Display a list view of the decklist with categories and preview image."""
    categories = {
        OPTcgCardCatagory.LEADER: [],
        OPTcgCardCatagory.CHARACTER: [],
        OPTcgCardCatagory.EVENT: [],
        OPTcgCardCatagory.STAGE: []
    }

    def get_card_info(card_id):
        return card_id2card_data.get(card_id)

    for card_id, count in decklist.items():
        card_data = get_card_info(card_id)
        category = card_data.card_category if card_data else OPTcgCardCatagory.CHARACTER
        if category not in categories:
            category = OPTcgCardCatagory.CHARACTER
        categories[category].append((card_id, count, card_data))

    for cat in categories:
        categories[cat].sort(key=lambda x: (x[2].cost if x[2] and x[2].cost is not None else 99, x[0]))

    def create_category_section(cat):
        cards = categories[cat]
        if not cards:
            return None

        card_rows = []
        total_count = sum(c[1] for c in cards)

        for card_id, count, card_data in cards:
            img_url = card_data.image_url if card_data else get_card_image_url(card_id, OPTcgLanguage.JP)
            name = card_data.name if card_data else card_id

            price_info = ""
            price_value = 0
            if card_data:
                if currency == CardCurrency.EURO and card_data.latest_eur_price:
                    price_value = card_data.latest_eur_price
                    price_info = f"{card_data.latest_eur_price:.2f}€"
                elif currency == CardCurrency.US_DOLLAR and card_data.latest_usd_price:
                    price_value = card_data.latest_usd_price
                    price_info = f"${card_data.latest_usd_price:.2f}"

            is_expensive = price_value > 5.0
            price_style = "font-family:'Share Tech Mono',monospace; font-size:0.72rem; color:" + (
                "#ef4444; font-weight:700;" if is_expensive else "#475569;"
            )

            preview_img_id = f"decklist-preview-image-{unique_id}"
            card_rows.append(
                ft.Div(
                    ft.Div(
                        ft.Span(str(count),
                                style="font-family:'Share Tech Mono',monospace; font-size:0.8rem; color:#94a3b8; width:1.25rem; text-align:center; flex-shrink:0;"),
                        ft.Span(f"{name} ({card_id})",
                                style="font-family:'Barlow',sans-serif; font-size:0.8rem; color:#38bdf8; margin-left:8px; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;"),
                        cls="flex items-center flex-1 cursor-pointer min-w-0",
                        hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest",
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    ft.A(price_info, href="#",
                         style=price_style + " flex-shrink:0; margin-left:8px; text-decoration:none;"
                         ) if price_info else "",
                    cls="flex items-center p-1 rounded group",
                    style="transition:background 0.12s;",
                    onmouseenter=f"this.style.background='#111d2e'; document.getElementById('{preview_img_id}').src='{img_url}'",
                    onmouseleave="this.style.background='';"
                )
            )

        return ft.Div(
            ft.Span(f"{cat.value} ({total_count})",
                    style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.75rem; color:#475569; text-transform:uppercase; display:block; padding-bottom:6px; margin-bottom:6px; border-bottom:1px solid #1a2540;"),
            ft.Div(*card_rows, cls="space-y-0"),
            cls="mb-4 break-inside-avoid"
        )

    left_cats = [OPTcgCardCatagory.LEADER, OPTcgCardCatagory.EVENT, OPTcgCardCatagory.STAGE]
    right_cats = [OPTcgCardCatagory.CHARACTER]

    left_column_content = [c for c in [create_category_section(cat) for cat in left_cats] if c]
    right_column_content = [c for c in [create_category_section(cat) for cat in right_cats] if c]

    preview_img_url = ""
    if leader_id:
        preview_img_url = card_id2card_data[leader_id].image_url if leader_id in card_id2card_data else get_card_image_url(leader_id, OPTcgLanguage.EN)
    else:
        first_card = list(decklist.keys())[0]
        preview_img_url = card_id2card_data[first_card].image_url if first_card in card_id2card_data else get_card_image_url(first_card, OPTcgLanguage.JP)

    return ft.Div(
        ft.Div(
            ft.Div(*left_column_content, cls="flex flex-col min-w-0"),
            ft.Div(*right_column_content, cls="flex flex-col min-w-0"),
            cls="flex-1 grid grid-cols-1 md:grid-cols-2 gap-x-6 gap-y-4 items-start"
        ),
        ft.Div(
            ft.Img(src=preview_img_url, id=f"decklist-preview-image-{unique_id}",
                   cls="w-full rounded-lg shadow-lg transition-all duration-300"),
            ft.Div(create_decklist_export_component(decklist, leader_id, unique_id), cls="mt-6"),
            cls="hidden lg:block w-64 flex-shrink-0 ml-4 sticky top-4 h-fit"
        ),
        cls="flex flex-col lg:flex-row"
    )


def display_decklist_modal(decklist: dict[str, int], card_id2card_data: dict[str, ExtendedCardData],
                            leader_id: str = None, currency: str = CardCurrency.EURO,
                            view_mode: str = DecklistViewMode.GRID, unique_id: str = "default"):
    """Display a visual representation of a decklist for the modal (without header)."""
    if view_mode == DecklistViewMode.LIST:
        return display_decklist_list_view(decklist, card_id2card_data, leader_id, currency, unique_id)

    filtered_decklist = {k: v for k, v in decklist.items() if k != leader_id} if leader_id else decklist
    card_items = []

    for card_id, count in filtered_decklist.items():
        img_url = card_id2card_data[card_id].image_url if card_id in card_id2card_data else get_card_image_url(card_id, OPTcgLanguage.JP)

        card_data = card_id2card_data.get(card_id)
        price_info = ""
        price_value = 0
        if card_data and hasattr(card_data, 'latest_eur_price') and hasattr(card_data, 'latest_usd_price'):
            if currency == CardCurrency.EURO and card_data.latest_eur_price:
                price_value = card_data.latest_eur_price
                price_info = f"€{card_data.latest_eur_price:.2f}"
            elif currency == CardCurrency.US_DOLLAR and card_data.latest_usd_price:
                price_value = card_data.latest_usd_price
                price_info = f"${card_data.latest_usd_price:.2f}"

        is_expensive = price_value > 5.0
        is_very_expensive = price_value > 20.0

        if is_very_expensive:
            price_style = "font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#ef4444; font-weight:700; background:rgba(239,68,68,0.12); padding:1px 4px; border-radius:3px;"
        elif is_expensive:
            price_style = "font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#ef4444; font-weight:700;"
        else:
            price_style = "font-family:'Share Tech Mono',monospace; font-size:0.68rem; color:#475569;"

        card_items.append(
            ft.Div(
                ft.Div(
                    ft.Img(src=img_url,
                           cls="w-full rounded cursor-pointer",
                           style="transition:opacity 0.15s;",
                           hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest",
                           hx_target="body",
                           hx_swap="beforeend"),
                    cls="cursor-pointer",
                ),
                ft.Div(
                    ft.Div(
                        ft.Span(f"x{count}",
                                style="font-family:'Share Tech Mono',monospace; font-size:0.78rem; color:#f1f5f9; font-weight:700;"),
                        ft.Span(f"💰 {price_info}" if is_expensive else price_info,
                                style=price_style) if price_info else ft.Span(""),
                        cls="flex justify-between items-center w-full",
                    ),
                    cls="mt-1 px-1",
                ),
                cls="mb-2"
            )
        )

    return ft.Div(
        ft.Div(*card_items,
               cls="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 xl:grid-cols-7 gap-2"),
        style="max-height:600px; overflow-y:auto;"
    )


def create_decklist_modal(
    leader_id: str,
    tournament_decklists: list,
    card_id2card_data: dict[str, ExtendedCardData],
    selected_tournament_id: str | None = None,
    selected_player_id: str | None = None,
    selected_currency: str = CardCurrency.EURO,
    days: str | None = None,
    placing: str | None = None,
    view_mode: str = DecklistViewMode.GRID,
    is_logged_in: bool = False,
    watchlisted_decklists: list[tuple[str, str]] | None = None,
) -> ft.Div:
    """Create a modal dialog for displaying tournament decklists."""
    import json as _json
    watchlisted_set = watchlisted_decklists or []
    watchlisted_keys = [f"{t}:{p}" for t, p in watchlisted_set]
    watchlisted_json = _json.dumps(watchlisted_keys)

    tournament_decklists.sort(key=lambda x: (x.placing is None, x.placing or float('inf')))

    decklist_options = []
    for td_obj in tournament_decklists:
        if not td_obj.tournament_id or not td_obj.player_id:
            continue
        option_text = []
        if td_obj.player_id:
            option_text.append(f"Player: {td_obj.player_id}")
        if td_obj.tournament_id:
            option_text.append(f"Tournament: {td_obj.tournament_id[:25]}{'...' if len(td_obj.tournament_id) > 25 else ''}")
        if td_obj.placing:
            option_text.append(f"Rank: #{td_obj.placing}")
        if hasattr(td_obj, 'date') and td_obj.date:
            option_text.append(f"Date: {td_obj.date}")
        value = f"{td_obj.tournament_id}:{td_obj.player_id}"
        decklist_options.append((" | ".join(option_text), value))

    selected_td = tournament_decklists[0] if tournament_decklists else None
    if selected_tournament_id and selected_player_id:
        for td in tournament_decklists:
            if td.tournament_id == selected_tournament_id and td.player_id == selected_player_id:
                selected_td = td
                break

    tournament_decklist_select_component = ft.Div()
    if decklist_options:
        selected_value = None
        if selected_td and selected_td.tournament_id and selected_td.player_id:
            selected_value = f"{selected_td.tournament_id}:{selected_td.player_id}"

        hidden_inputs = [ft.Input(type="hidden", name="lid", value=leader_id)]
        if days is not None:
            hidden_inputs.append(ft.Input(type="hidden", name="days", value=days))
        if placing is not None:
            hidden_inputs.append(ft.Input(type="hidden", name="placing", value=placing))

        hidden_inputs.append(
            ft.Input(
                type="hidden", name="view_mode", id="view-mode-input", value=view_mode,
                hx_get="/api/decklist/tournament-decklist-modal",
                hx_target="#selected-tournament-decklist-content-modal",
                hx_include="#tournament-decklist-select-modal, #currency-select-modal, [name='lid'], [name='meta_format'], [name='days'], [name='placing']",
                hx_trigger="change",
                hx_vals='''js:{
                    "tournament_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[0],
                    "player_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[1]
                }''',
                hx_indicator="#tournament-decklist-loading"
            )
        )

        grid_active = view_mode == DecklistViewMode.GRID
        list_active = view_mode == DecklistViewMode.LIST

        tournament_decklist_select_component = ft.Div(
            *hidden_inputs,
            ft.Div(
                ft.Div(
                    ft.Span("Tournament Decklist", style=_LABEL_STYLE),
                    ft.Select(
                        *[
                            ft.Option(text, value=value, selected=(value == selected_value),
                                      data_meta_format=str(td_obj.meta_format) if td_obj.meta_format else "")
                            for (text, value), td_obj in zip(decklist_options, [
                                td for td in tournament_decklists if td.tournament_id and td.player_id
                            ])
                        ],
                        id="tournament-decklist-select-modal",
                        cls="meta-select styled-select",
                        hx_get="/api/decklist/tournament-decklist-modal",
                        hx_target="#selected-tournament-decklist-content-modal",
                        hx_include="[name='lid'], [name='meta_format'], [name='days'], [name='placing'], #currency-select-modal, #view-mode-input",
                        hx_trigger="change",
                        hx_swap="innerHTML",
                        hx_vals='''js:{
                            "tournament_id": event.target.value.split(":")[0],
                            "player_id": event.target.value.split(":")[1]
                        }''',
                        hx_indicator="#tournament-decklist-loading",
                        onchange='(function(){try{const p=new URLSearchParams(window.location.search);const v=document.getElementById("tournament-decklist-select-modal").value.split(":");p.set("tournament_id",v[0]);p.set("player_id",v[1]);const c=document.getElementById("currency-select-modal");if(c&&c.value){p.set("currency",c.value)}p.set("modal","decklist");const u=window.location.pathname+"?"+p.toString();window.history.replaceState({},"",u);}catch(e){}})()'
                    ),
                    cls="flex-1",
                ),
                ft.Div(
                    ft.Span("Currency", style=_LABEL_STYLE),
                    ft.Select(
                        ft.Option("EUR (€)", value=CardCurrency.EURO, selected=(selected_currency == CardCurrency.EURO)),
                        ft.Option("USD ($)", value=CardCurrency.US_DOLLAR, selected=(selected_currency == CardCurrency.US_DOLLAR)),
                        id="currency-select-modal",
                        name="currency",
                        cls="meta-select styled-select",
                        hx_get="/api/decklist/tournament-decklist-modal",
                        hx_target="#selected-tournament-decklist-content-modal",
                        hx_include="#tournament-decklist-select-modal, [name='lid'], [name='meta_format'], [name='days'], [name='placing'], #view-mode-input",
                        hx_trigger="change",
                        hx_swap="innerHTML",
                        hx_vals='''js:{
                            "tournament_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[0],
                            "player_id": document.getElementById("tournament-decklist-select-modal").value.split(":")[1]
                        }''',
                        hx_indicator="#tournament-decklist-loading",
                        onchange='(function(){try{const p=new URLSearchParams(window.location.search);const v=document.getElementById("tournament-decklist-select-modal").value.split(":");p.set("tournament_id",v[0]);p.set("player_id",v[1]);const c=document.getElementById("currency-select-modal");if(c&&c.value){p.set("currency",c.value)}p.set("modal","decklist");const u=window.location.pathname+"?"+p.toString();window.history.replaceState({},"",u);}catch(e){}})()'
                    ),
                    cls="flex-none w-full sm:w-36 sm:ml-4",
                ),
                ft.Div(
                    ft.Span("View", style=_LABEL_STYLE),
                    ft.Div(
                        ft.Button(
                            "Grid",
                            cls=f"dm-view-btn {'active' if grid_active else ''}",
                            onclick=f"this.classList.add('active'); this.nextElementSibling.classList.remove('active'); document.getElementById('view-mode-input').value='{DecklistViewMode.GRID}'; htmx.trigger('#view-mode-input', 'change');",
                        ),
                        ft.Button(
                            "List",
                            cls=f"dm-view-btn {'active' if list_active else ''}",
                            onclick=f"this.classList.add('active'); this.previousElementSibling.classList.remove('active'); document.getElementById('view-mode-input').value='{DecklistViewMode.LIST}'; htmx.trigger('#view-mode-input', 'change');",
                        ),
                        cls="flex",
                    ),
                    cls="flex-none ml-0 sm:ml-4",
                ),
                cls="flex flex-col sm:flex-row sm:items-start gap-4",
            ),
            create_loading_spinner(id="tournament-decklist-loading", size="w-6 h-6",
                                   container_classes="min-h-[40px] hidden"),
            cls="mb-5",
        )

    # Tournament stats
    tournament_stats = ft.Div()
    if tournament_decklists:
        total_tournaments = len(set(td.tournament_id for td in tournament_decklists))
        total_players = len(tournament_decklists)
        top_8_count = len([td for td in tournament_decklists if td.placing and td.placing <= 8])
        wins = len([td for td in tournament_decklists if td.placing and td.placing == 1])

        def _stat(value, label, color):
            return ft.Div(
                ft.Span(str(value), style=_STAT_VALUE + f"color:{color};"),
                ft.Span(label, style=_STAT_LABEL),
                style=_PANEL_STYLE + " text-align:center;",
            )

        tournament_stats = ft.Div(
            ft.Span("Tournament Performance",
                    style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9; display:block; margin-bottom:12px;"),
            ft.Div(
                _stat(total_tournaments, "Tournaments", "#38bdf8"),
                _stat(total_players,    "Decklists",   "#10b981"),
                _stat(top_8_count,      "Top 8",       "#f59e0b"),
                _stat(wins,             "Wins",        "#94a3b8"),
                cls="grid grid-cols-2 sm:grid-cols-4 gap-3",
            ),
            cls="mb-5",
        )

    # Initial decklist content
    initial_decklist_content = ft.Div()
    if selected_td and selected_td.decklist:
        decklist_display = display_decklist_modal(
            selected_td.decklist, card_id2card_data, leader_id,
            selected_currency or CardCurrency.EURO, view_mode=view_mode, unique_id="initial"
        )
        if view_mode == DecklistViewMode.LIST:
            initial_decklist_content = decklist_display
        else:
            initial_decklist_content = ft.Div(
                decklist_display,
                create_decklist_export_component(selected_td.decklist, leader_id, "initial")
            )
    else:
        initial_decklist_content = ft.Div(
            ft.P("Select a tournament decklist from the dropdown above to view details.",
                 style="font-family:'Barlow',sans-serif; color:#475569; text-align:center; padding:32px 0;"),
        )

    return ft.Div(
        ft.Div(
            ft.Div(
                # ── Toolbar (share / watchlist / close) ──────────────────────
                ft.Div(
                    # Share button
                    ft.Button(
                        ft.Span(
                            ft.Span("🔗", cls="text-base"),
                            ft.Span("Copy link", cls="hidden sm:inline"),
                            cls="inline-flex items-center gap-2"
                        ),
                        type="button",
                        title="Copy shareable link",
                        cls="ml-2 inline-flex items-center gap-2 rounded-full px-4 py-2 font-semibold shadow-sm active:translate-y-px transition",
                        style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.08em; font-size:0.75rem; background:#f59e0b; color:#000; border:none; cursor:pointer;",
                        onclick='(function(evt){evt.preventDefault();var btn=evt.currentTarget; (async function(){ try{function buildShareURL(){const p=new URLSearchParams(window.location.search);const lidInput=document.querySelector("[name=lid]");if(lidInput&&lidInput.value){p.set("lid",lidInput.value);}const daysInput=document.querySelector("[name=days]");if(daysInput&&daysInput.value){p.set("days",daysInput.value);}const placingInput=document.querySelector("[name=placing]");if(placingInput&&placingInput.value){p.set("placing",placingInput.value);}const sel=document.getElementById("tournament-decklist-select-modal");if(sel&&sel.value){const v=sel.value.split(":");p.set("tournament_id",v[0]);p.set("player_id",v[1]);}const c=document.getElementById("currency-select-modal");if(c&&c.value){p.set("currency",c.value)}p.set("modal","decklist");return window.location.origin+window.location.pathname+"?"+p.toString();}const url=buildShareURL(); try{ if(navigator.clipboard&&navigator.clipboard.writeText){ await navigator.clipboard.writeText(url); } else { throw new Error("no-async-clipboard"); } } catch(e){ var ta=document.createElement("textarea"); ta.value=url; document.body.appendChild(ta); ta.select(); document.execCommand("copy"); document.body.removeChild(ta); } if(!btn) return; var orig=btn.getAttribute("data-orig-html"); if(!orig){orig=btn.innerHTML; btn.setAttribute("data-orig-html", orig);} btn.innerHTML = "<span class=\"inline-flex items-center gap-2\">✅ <span class=\"hidden sm:inline\">Copied!</span></span>"; btn.classList.add("ring-2","ring-green-400"); setTimeout(function(){btn.innerHTML=orig; btn.classList.remove("ring-2","ring-green-400");}, 1500); } catch(e){} })(); })(event)'
                    ),
                    *(
                        [create_decklist_watchlist_toggle(
                            leader_id=leader_id,
                            tournament_id=selected_td.tournament_id if selected_td else "",
                            player_id=selected_td.player_id if selected_td else "",
                            meta_format=str(selected_td.meta_format) if selected_td and selected_td.meta_format else "",
                            is_in_watchlist=bool(selected_td and f"{selected_td.tournament_id}:{selected_td.player_id}" in watchlisted_keys),
                            include_script=True,
                        )]
                        if is_logged_in and selected_td else []
                    ),
                    # Close button
                    ft.Button(
                        ft.Span("×", style="font-size:1.2rem; line-height:1;"),
                        type="button",
                        cls="inline-flex items-center justify-center w-9 h-9 rounded-full transition",
                        style="background:rgba(8,14,28,0.9); border:1px solid #1a2540; color:#94a3b8; cursor:pointer;",
                        onclick='event.stopPropagation();(function(){try{const p=new URLSearchParams(window.location.search);p.delete("tournament_id");p.delete("player_id");p.delete("currency");p.delete("modal");const u=window.location.pathname+(p.toString()?"?"+p.toString():"");window.history.replaceState({},"",u);}catch(e){};var el=document.getElementById("decklist-modal-backdrop");if(el)el.remove();})()'
                    ),
                    cls="absolute top-4 right-4 flex items-center gap-2",
                ),

                # ── Header ────────────────────────────────────────────────────
                ft.Div(
                    ft.Div(
                        ft.A(
                            ft.Img(
                                src=card_id2card_data[leader_id].image_url if leader_id in card_id2card_data else get_card_image_url(leader_id, OPTcgLanguage.EN),
                                alt=f"{leader_id} card",
                                cls="w-full h-full object-cover rounded-lg shadow-2xl",
                                style="max-width:180px; max-height:250px; border:2px solid rgba(245,158,11,0.4);",
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
                        cls="decklist-modal-leader-card flex-shrink-0 mb-4 sm:mb-0 sm:mr-6",
                    ),
                    ft.Div(
                        ft.H2("Tournament Decklists",
                              style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.12em; font-size:1.8rem; color:#f1f5f9; line-height:1; margin-bottom:8px; padding-right:4rem;"),
                        ft.Div(
                            ft.Span(leader_id,
                                    style="font-family:'Share Tech Mono',monospace; font-size:0.78rem; color:#f59e0b; background:rgba(245,158,11,0.1); border:1px solid rgba(245,158,11,0.3); border-radius:20px; padding:3px 10px; display:inline-block;"),
                            cls="mb-3",
                        ),
                        ft.P(f"Explore {len(tournament_decklists)} tournament decklists from competitive play",
                             style="font-family:'Barlow',sans-serif; font-size:0.82rem; color:#475569;"),
                        cls="flex-1 flex flex-col justify-center",
                    ),
                    cls="flex flex-col sm:flex-row items-center sm:items-start mb-5 pb-5",
                    style="border-bottom:1px solid #1a2540;",
                ),

                # ── Scrollable body ───────────────────────────────────────────
                ft.Div(
                    tournament_stats,
                    tournament_decklist_select_component,

                    # Decklist display panel
                    ft.Div(
                        ft.Span("Selected Tournament Decklist",
                                style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9; display:block; margin-bottom:12px;"),
                        ft.Div(
                            initial_decklist_content,
                            id="selected-tournament-decklist-content-modal",
                            cls="min-h-[400px]",
                        ),
                        style=_PANEL_STYLE,
                    ) if tournament_decklists else ft.Div(
                        ft.P("No tournament decklists available for this leader.",
                             style="font-family:'Barlow',sans-serif; color:#475569; text-align:center; padding:32px 0;"),
                    ),

                    cls="max-h-[60vh] overflow-y-auto",
                ),

                style="background:#0d1424; border:1px solid #1a2540; border-radius:12px; padding:16px; max-width:72rem; width:100%; margin:0 0.5rem; position:relative;",
                onclick="event.stopPropagation()"
            ),
            cls="decklist-modal-backdrop fixed inset-0 bg-black bg-opacity-80 flex items-start justify-center overflow-y-auto py-4",
            onclick='if (event.target === this) { (function(){try{const p=new URLSearchParams(window.location.search);p.delete("tournament_id");p.delete("player_id");p.delete("currency");p.delete("modal");const u=window.location.pathname+(p.toString()?"?"+p.toString():"");window.history.replaceState({},"",u);}catch(e){};var el=document.getElementById("decklist-modal-backdrop");if(el)el.remove();})() }',
            id="decklist-modal-backdrop",
            data_watchlisted_decklists=watchlisted_json,
        ),

        ft.Style("""
            .decklist-modal-backdrop {
                z-index: 9999 !important;
                backdrop-filter: blur(4px);
                overflow-x: hidden !important;
                overflow-y: auto !important;
                max-width: 100vw !important;
            }
            .carousel-item { display: none; }
            .carousel-item.active { display: block; }

            /* View toggle buttons */
            .dm-view-btn {
                font-family: 'Bebas Neue', sans-serif;
                letter-spacing: 0.08em;
                font-size: 0.72rem;
                padding: 8px 16px;
                background: #080e1c;
                border: 1px solid #1a2540;
                color: #475569;
                cursor: pointer;
                transition: all 0.12s;
            }
            .dm-view-btn:first-child { border-radius: 6px 0 0 6px; }
            .dm-view-btn:last-child  { border-radius: 0 6px 6px 0; border-left: none; }
            .dm-view-btn.active {
                background: rgba(56,189,248,0.1);
                color: #38bdf8;
                border-color: rgba(56,189,248,0.3);
            }
            .dm-view-btn:last-child.active { border-left: 1px solid rgba(56,189,248,0.3); }

            /* Meta select inside modal (need to declare since modal may render before sidebar) */
            .meta-select {
                width: 100%;
                background: #080e1c;
                color: #f1f5f9;
                border: 1px solid #1a2540;
                border-radius: 8px;
                padding: 8px 12px;
                font-family: 'Barlow', sans-serif;
                font-size: 0.875rem;
                outline: none;
                cursor: pointer;
                transition: border-color 0.15s, box-shadow 0.15s;
            }
            .meta-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }

            #tournament-decklist-loading.htmx-request { display: block !important; }

            /* Card modals appear above decklist modal */
            .modal-backdrop:not(.decklist-modal-backdrop) { z-index: 10000 !important; }

            body:has(.decklist-modal-backdrop) {
                overflow-x: hidden !important;
                max-width: 100vw !important;
            }

            @media (max-width: 640px) {
                .decklist-modal-backdrop > div {
                    max-width: 100vw !important;
                    margin: 0 !important;
                    box-sizing: border-box !important;
                }
            }
        """),

        # JavaScript (unchanged)
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
                if (evt.target.classList && evt.target.classList.contains('modal-backdrop') &&
                    !evt.target.classList.contains('decklist-modal-backdrop')) {
                    evt.preventDefault();
                    evt.target.remove();
                }
            });

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
