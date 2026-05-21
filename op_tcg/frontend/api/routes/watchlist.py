import json
import re
from fasthtml import ft
from starlette.requests import Request
from starlette.responses import JSONResponse
from op_tcg.backend.db import (
    add_to_watchlist, remove_from_watchlist, update_watchlist_tags, update_watchlist_quantity, get_watchlist,
    add_decklist_to_watchlist, remove_decklist_from_watchlist, update_decklist_watchlist_tags,
    create_custom_decklist, get_custom_decklists, update_custom_decklist, delete_custom_decklist,
    DEFAULT_WATCHLIST_TAG,
)
from op_tcg.frontend.utils.extract import (
    get_watchlist_aggregate_price_data, get_card_id_card_data_lookup,
    get_all_tournament_decklist_data, get_card_popularity_data,
)
from op_tcg.frontend.api.models import CardPopularityParams
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.backend.models.cards import OPTcgCardCatagory
from op_tcg.frontend.utils.charts import create_price_development_chart
from op_tcg.frontend.utils.decklist import DecklistViewMode, decklist_to_export_str, ensure_leader_id
from op_tcg.frontend.components.decklist_modal import display_decklist_modal

# ── Design-system helpers ───────────────────────────────────────────────────
# Shared inline styles for view-toggle buttons (Grid / List)
_TAB_ACTIVE   = "background:rgba(245,158,11,.12);color:#f59e0b;border:1px solid rgba(245,158,11,.35);"
_TAB_INACTIVE = "background:#0d1424;color:#475569;border:1px solid #1a2540;"

# Shared inline style for the edit-tag pencil icon button
_EDIT_BTN_STYLE = (
    "color:#475569;background:transparent;border:none;cursor:pointer;"
    "margin-left:4px;padding:0 2px;transition:color .15s;"
)


def _parse_tags(raw) -> list:
    if isinstance(raw, list):
        tags = [t.strip() for t in raw if str(t).strip()]
    elif isinstance(raw, str):
        tags = [t.strip() for t in raw.split(',') if t.strip()]
    else:
        tags = []
    return tags or [DEFAULT_WATCHLIST_TAG]


def _tag_chips_component(card_id: str, card_version: int, language: str, tags: list):
    target_id = f"tags-{card_id}-{card_version}-{language}"
    tags_str = ",".join(tags)
    return ft.Div(
        *[ft.Span(tag, cls="wl-tag") for tag in tags],
        ft.Button(
            ft.I(cls="fas fa-pen text-xs"),
            type="button",
            style=_EDIT_BTN_STYLE,
            title="Edit tags",
            hx_get=f"/api/watchlist/tag-editor?card_id={card_id}&card_version={card_version}&language={language}&tags={tags_str}",
            hx_target=f"#{target_id}",
            hx_swap="outerHTML",
        ),
        id=target_id,
        cls="flex flex-wrap items-center mt-1",
        onclick="event.stopPropagation();"
    )


def _tag_editor_component(card_id: str, card_version: int, language: str, tags: list):
    target_id = f"tags-{card_id}-{card_version}-{language}"
    tags_str = ",".join(tags)
    return ft.Form(
        ft.Input(type="hidden", name="card_id", value=card_id),
        ft.Input(type="hidden", name="card_version", value=str(card_version)),
        ft.Input(type="hidden", name="language", value=language),
        ft.Div(
            ft.Input(
                type="text",
                name="tags",
                value=tags_str,
                placeholder="my collection",
                cls="wl-input",
                style="font-size:.75rem;padding:4px 8px;",
                autofocus=True,
                onkeydown="event.stopPropagation();",
                onkeyup="event.stopPropagation();",
                onkeypress="event.stopPropagation();",
            ),
            ft.Div(
                ft.Button(
                    "Save",
                    type="submit",
                    cls="wl-btn-primary",
                    style="font-size:.75rem;padding:4px 10px;",
                ),
                ft.Button(
                    "Cancel",
                    type="button",
                    cls="wl-btn-ghost",
                    style="font-size:.75rem;padding:4px 10px;margin-left:4px;",
                    hx_get=f"/api/watchlist/tag-chips?card_id={card_id}&card_version={card_version}&language={language}&tags={tags_str}",
                    hx_target=f"#{target_id}",
                    hx_swap="outerHTML",
                ),
                cls="flex items-center mt-1"
            ),
            cls="flex flex-col w-full max-w-xs"
        ),
        id=target_id,
        hx_post="/api/watchlist/tags",
        hx_target=f"#{target_id}",
        hx_swap="outerHTML",
        cls="flex items-start mt-1",
        onclick="event.stopPropagation();"
    )


def setup_watchlist_routes(rt):

    @rt("/api/watchlist/add", methods=["POST"])
    async def add_watchlist(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        card_id = data.get('card_id')
        card_version = 0 if data.get('card_version') in (None, 'Base', 0) else int(data.get('card_version', 0))
        language = data.get('language', 'English')
        tags = _parse_tags(data.get('tags', [DEFAULT_WATCHLIST_TAG]))

        if not card_id:
            return JSONResponse({"error": "Missing card_id"}, status_code=400)

        user_id = user.get('sub')
        add_to_watchlist(user_id, card_id, card_version, language, tags)

        return JSONResponse({"status": "success", "message": "Card added to watchlist"})

    @rt("/api/watchlist/remove", methods=["POST"])
    async def remove_watchlist(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        card_id = data.get('card_id')
        card_version = 0 if data.get('card_version') in (None, 'Base', 0) else int(data.get('card_version', 0))
        language = data.get('language', 'en')

        if not card_id:
            return JSONResponse({"error": "Missing card_id"}, status_code=400)

        user_id = user.get('sub')
        remove_from_watchlist(user_id, card_id, card_version, language)

        return JSONResponse({"status": "success", "message": "Card removed from watchlist"})

    @rt("/api/watchlist/quantity", methods=["POST"])
    async def update_quantity(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        card_id = data.get('card_id')
        card_version = 0 if data.get('card_version') in (None, 'Base', 0) else int(data.get('card_version', 0))
        language = data.get('language', 'en')

        if not card_id:
            return JSONResponse({"error": "Missing card_id"}, status_code=400)

        try:
            quantity = max(1, int(data.get('quantity', 1)))
        except (ValueError, TypeError):
            quantity = 1

        user_id = user.get('sub')
        update_watchlist_quantity(user_id, card_id, card_version, language, quantity)

        return JSONResponse({"status": "success", "quantity": quantity})

    @rt("/api/watchlist/tags", methods=["POST"])
    async def update_tags(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        form = await request.form()
        card_id = form.get('card_id')
        card_version_raw = form.get('card_version', '0')
        card_version = 0 if card_version_raw in (None, 'Base', '0', '') else int(card_version_raw)
        language = form.get('language', 'en')
        tags = _parse_tags(form.get('tags', DEFAULT_WATCHLIST_TAG))

        if not card_id:
            return JSONResponse({"error": "Missing card_id"}, status_code=400)

        user_id = user.get('sub')
        update_watchlist_tags(user_id, card_id, card_version, language, tags)

        return _tag_chips_component(card_id, card_version, language, tags)

    @rt("/api/watchlist/tag-editor", methods=["GET"])
    async def tag_editor(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        card_id = request.query_params.get('card_id', '')
        card_version = int(request.query_params.get('card_version', 0))
        language = request.query_params.get('language', 'en')
        tags = _parse_tags(request.query_params.get('tags', DEFAULT_WATCHLIST_TAG))

        return _tag_editor_component(card_id, card_version, language, tags)

    @rt("/api/watchlist/tag-chips", methods=["GET"])
    async def tag_chips_view(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        card_id = request.query_params.get('card_id', '')
        card_version = int(request.query_params.get('card_version', 0))
        language = request.query_params.get('language', 'en')
        tags = _parse_tags(request.query_params.get('tags', DEFAULT_WATCHLIST_TAG))

        return _tag_chips_component(card_id, card_version, language, tags)

    @rt("/api/watchlist/aggregate-chart", methods=["GET"])
    async def aggregate_chart(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        tag_filter = request.query_params.get('tag', '')
        try:
            days = int(request.query_params.get('days', 90))
        except (ValueError, TypeError):
            days = 90

        user_id = user.get('sub')
        watchlist = get_watchlist(user_id)

        if tag_filter:
            watchlist = [item for item in watchlist if tag_filter in item.get('tags', [DEFAULT_WATCHLIST_TAG])]

        card_versions = []
        for item in watchlist:
            card_id = item.get('card_id')
            version_val = item.get('card_version', 0)
            try:
                aa_version = int(version_val) if version_val not in (None, 'Base') else 0
            except (ValueError, TypeError):
                aa_version = 0
            quantity = max(1, int(item.get('quantity', 1)))
            if card_id:
                card_versions.append((card_id, aa_version, quantity))

        if not card_versions:
            return ft.Div(
                ft.P("No cards in this collection.", style="color:#475569;font-size:.875rem;text-align:center;padding:24px 0;"),
                cls="h-full flex items-center justify-center"
            )

        try:
            price_data = get_watchlist_aggregate_price_data(card_versions, days=days)
        except Exception:
            return ft.Div(
                ft.P("Could not load price data.", style="color:#475569;font-size:.875rem;text-align:center;padding:24px 0;"),
                cls="h-full flex items-center justify-center"
            )

        if not price_data.get('eur') and not price_data.get('usd'):
            return ft.Div(
                ft.P("No price history available for the selected period.", style="color:#475569;font-size:.875rem;text-align:center;padding:24px 0;"),
                cls="h-full flex items-center justify-center"
            )

        # Build release event markers from data already returned by the aggregate query
        release_events = []
        try:
            raw_releases = price_data.get('releases', [])
            if raw_releases:
                card_lookup = get_card_id_card_data_lookup()
                for r in raw_releases:
                    card = card_lookup.get(r['card_id'])
                    name = card.name if card else r['card_id']
                    aa_label = f" (Alt Art {r['aa_version']})" if r['aa_version'] else ""
                    set_code = r['card_id'].split('-')[0] if '-' in r['card_id'] else ''
                    set_label = f" ({set_code})" if set_code else ""
                    release_events.append({'date': r['date'], 'label': f"{name}{aa_label}{set_label}"})
        except Exception:
            pass  # Release markers are non-critical

        label = f'"{tag_filter}"' if tag_filter else "All Cards"
        chart_id = f"portfolio-aggregate-chart-{days}-{tag_filter.replace(' ', '-') or 'all'}"

        return create_price_development_chart(
            container_id=chart_id,
            price_data=price_data,
            card_name=f"Portfolio · {label}",
            show_x_axis=True,
            show_legend=True,
            release_events=release_events,
        )

    # ── Decklist watchlist routes ───────────────────────────────────────────

    def _dl_tag_chips(leader_id: str, tournament_id: str, player_id: str, tags: list):
        safe_tid = re.sub(r'[^a-zA-Z0-9_\-]', '_', tournament_id)[:20]
        safe_pid = re.sub(r'[^a-zA-Z0-9_\-]', '_', player_id)[:20]
        target_id = f"tags-dl-{leader_id}-{safe_tid}-{safe_pid}"
        tags_str = ",".join(tags)
        return ft.Div(
            *[ft.Span(tag, cls="wl-tag") for tag in tags],
            ft.Button(
                ft.I(cls="fas fa-pen text-xs"),
                type="button",
                style=_EDIT_BTN_STYLE,
                title="Edit tags",
                hx_get=f"/api/watchlist/decklist/tag-editor?leader_id={leader_id}&tournament_id={tournament_id}&player_id={player_id}&tags={tags_str}",
                hx_target=f"#{target_id}",
                hx_swap="outerHTML",
            ),
            id=target_id,
            cls="flex flex-wrap items-center mt-1",
            onclick="event.stopPropagation();"
        )

    def _dl_tag_editor(leader_id: str, tournament_id: str, player_id: str, tags: list):
        safe_tid = re.sub(r'[^a-zA-Z0-9_\-]', '_', tournament_id)[:20]
        safe_pid = re.sub(r'[^a-zA-Z0-9_\-]', '_', player_id)[:20]
        target_id = f"tags-dl-{leader_id}-{safe_tid}-{safe_pid}"
        tags_str = ",".join(tags)
        return ft.Form(
            ft.Input(type="hidden", name="leader_id", value=leader_id),
            ft.Input(type="hidden", name="tournament_id", value=tournament_id),
            ft.Input(type="hidden", name="player_id", value=player_id),
            ft.Div(
                ft.Input(
                    type="text",
                    name="tags",
                    value=tags_str,
                    placeholder="my decklists",
                    cls="wl-input",
                    style="font-size:.75rem;padding:4px 8px;",
                    autofocus=True,
                    onkeydown="event.stopPropagation();",
                    onkeyup="event.stopPropagation();",
                    onkeypress="event.stopPropagation();",
                ),
                ft.Div(
                    ft.Button(
                        "Save",
                        type="submit",
                        cls="wl-btn-primary",
                        style="font-size:.75rem;padding:4px 10px;",
                    ),
                    ft.Button(
                        "Cancel",
                        type="button",
                        cls="wl-btn-ghost",
                        style="font-size:.75rem;padding:4px 10px;margin-left:4px;",
                        hx_get=f"/api/watchlist/decklist/tag-chips?leader_id={leader_id}&tournament_id={tournament_id}&player_id={player_id}&tags={tags_str}",
                        hx_target=f"#{target_id}",
                        hx_swap="outerHTML",
                    ),
                    cls="flex items-center mt-1"
                ),
                cls="flex flex-col w-full max-w-xs"
            ),
            id=target_id,
            hx_post="/api/watchlist/decklist/tags",
            hx_target=f"#{target_id}",
            hx_swap="outerHTML",
            cls="flex items-start mt-1",
            onclick="event.stopPropagation();"
        )

    def _custom_tag_chips(custom_id: str, tags: list):
        target_id = f"tags-cdl-{re.sub(r'[^a-zA-Z0-9_-]', '_', custom_id)[:20]}"
        tags_str = ",".join(tags)
        return ft.Div(
            *[ft.Span(tag, cls="wl-tag") for tag in tags],
            ft.Button(
                ft.I(cls="fas fa-pen text-xs"),
                type="button",
                style=_EDIT_BTN_STYLE,
                title="Edit tags",
                hx_get=f"/api/watchlist/custom-decklist/tag-editor?custom_id={custom_id}&tags={tags_str}",
                hx_target=f"#{target_id}",
                hx_swap="outerHTML",
            ),
            id=target_id,
            cls="flex flex-wrap items-center mt-1",
            onclick="event.stopPropagation();"
        )

    def _custom_tag_editor(custom_id: str, tags: list):
        target_id = f"tags-cdl-{re.sub(r'[^a-zA-Z0-9_-]', '_', custom_id)[:20]}"
        tags_str = ",".join(tags)
        return ft.Form(
            ft.Input(type="hidden", name="custom_id", value=custom_id),
            ft.Div(
                ft.Input(
                    type="text",
                    name="tags",
                    value=tags_str,
                    placeholder="my decklists",
                    cls="wl-input",
                    style="font-size:.75rem;padding:4px 8px;",
                    autofocus=True,
                    onkeydown="event.stopPropagation();",
                    onkeyup="event.stopPropagation();",
                    onkeypress="event.stopPropagation();",
                ),
                ft.Div(
                    ft.Button(
                        "Save",
                        type="submit",
                        cls="wl-btn-primary",
                        style="font-size:.75rem;padding:4px 10px;",
                    ),
                    ft.Button(
                        "Cancel",
                        type="button",
                        cls="wl-btn-ghost",
                        style="font-size:.75rem;padding:4px 10px;margin-left:4px;",
                        hx_get=f"/api/watchlist/custom-decklist/tag-chips?custom_id={custom_id}&tags={tags_str}",
                        hx_target=f"#{target_id}",
                        hx_swap="outerHTML",
                    ),
                    cls="flex items-center mt-1"
                ),
                cls="flex flex-col w-full max-w-xs"
            ),
            id=target_id,
            hx_post="/api/watchlist/custom-decklist/tags",
            hx_target=f"#{target_id}",
            hx_swap="outerHTML",
            cls="flex items-start mt-1",
            onclick="event.stopPropagation();"
        )

    @rt("/api/watchlist/decklist/add", methods=["POST"])
    async def decklist_add(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        leader_id = data.get('leader_id')
        tournament_id = data.get('tournament_id')
        player_id = data.get('player_id')
        if not all([leader_id, tournament_id, player_id]):
            return JSONResponse({"error": "Missing required fields"}, status_code=400)
        meta_format = data.get('meta_format', '')
        tags = _parse_tags(data.get('tags', [DEFAULT_WATCHLIST_TAG]))
        td = next(
            (x for x in get_all_tournament_decklist_data()
             if x.tournament_id == tournament_id and x.player_id == player_id),
            None,
        )
        tournament_timestamp = td.tournament_timestamp if td else None
        decklist_id = td.decklist_id if td else None
        add_decklist_to_watchlist(user.get('sub'), leader_id, tournament_id, player_id, meta_format, tags, tournament_timestamp, decklist_id)
        return JSONResponse({"status": "success"})

    @rt("/api/watchlist/decklist/remove", methods=["POST"])
    async def decklist_remove(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        leader_id = data.get('leader_id')
        tournament_id = data.get('tournament_id')
        player_id = data.get('player_id')
        if not all([leader_id, tournament_id, player_id]):
            return JSONResponse({"error": "Missing required fields"}, status_code=400)
        remove_decklist_from_watchlist(user.get('sub'), leader_id, tournament_id, player_id)
        return JSONResponse({"status": "success"})

    @rt("/api/watchlist/decklist/tags", methods=["POST"])
    async def decklist_update_tags(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        form = await request.form()
        leader_id = form.get('leader_id', '')
        tournament_id = form.get('tournament_id', '')
        player_id = form.get('player_id', '')
        tags = _parse_tags(form.get('tags', DEFAULT_WATCHLIST_TAG))
        if not all([leader_id, tournament_id, player_id]):
            return JSONResponse({"error": "Missing required fields"}, status_code=400)
        update_decklist_watchlist_tags(user.get('sub'), leader_id, tournament_id, player_id, tags)
        return _dl_tag_chips(leader_id, tournament_id, player_id, tags)

    @rt("/api/watchlist/decklist/tag-editor", methods=["GET"])
    async def decklist_tag_editor(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        p = request.query_params
        leader_id = p.get('leader_id', '')
        tournament_id = p.get('tournament_id', '')
        player_id = p.get('player_id', '')
        tags = _parse_tags(p.get('tags', DEFAULT_WATCHLIST_TAG))
        return _dl_tag_editor(leader_id, tournament_id, player_id, tags)

    @rt("/api/watchlist/decklist/tag-chips", methods=["GET"])
    async def decklist_tag_chips_view(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        p = request.query_params
        leader_id = p.get('leader_id', '')
        tournament_id = p.get('tournament_id', '')
        player_id = p.get('player_id', '')
        tags = _parse_tags(p.get('tags', DEFAULT_WATCHLIST_TAG))
        return _dl_tag_chips(leader_id, tournament_id, player_id, tags)

    @rt("/api/watchlist/decklist/inline-cards", methods=["GET"])
    async def decklist_inline_cards(request: Request):
        """Return a compact inline decklist view for the watchlist page."""
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        p = request.query_params
        leader_id = p.get('leader_id', '')
        tournament_id = p.get('tournament_id', '')
        player_id = p.get('player_id', '')
        view_mode = p.get('view_mode', DecklistViewMode.GRID)

        if not all([leader_id, tournament_id, player_id]):
            return ft.P("Missing parameters.", style="color:#ef4444;font-size:.875rem;padding:.75rem;")

        # Cached lookup — fast after first call
        all_decklists = get_all_tournament_decklist_data()
        selected = next(
            (td for td in all_decklists if td.tournament_id == tournament_id and td.player_id == player_id),
            None
        )

        if not selected or not selected.decklist:
            return ft.P("Decklist not found.", style="color:#475569;font-size:.875rem;padding:.75rem;")

        card_id2card_data = get_card_id_card_data_lookup()
        total_cards = sum(selected.decklist.values())

        # Construct a stable container ID matching the one on the watchlist page
        safe_tid = re.sub(r'[^a-zA-Z0-9_\-]', '_', tournament_id)[:20]
        safe_pid = re.sub(r'[^a-zA-Z0-9_\-]', '_', player_id)[:20]
        container_id = f"dl-cards-{leader_id}-{safe_tid}-{safe_pid}"
        unique_id = f"{safe_tid}-{safe_pid}"

        # Build export string for copy-to-sim
        export_str = decklist_to_export_str(ensure_leader_id(selected.decklist, leader_id))
        copy_btn_id = f"decklist-copy-btn-{unique_id}"
        export_pre_id = f"decklist-export-{unique_id}"

        base_url = f"/api/watchlist/decklist/inline-cards?leader_id={leader_id}&tournament_id={tournament_id}&player_id={player_id}"

        view_toggle = ft.Div(
            ft.Button(
                ft.I(cls="fas fa-th-large mr-1"), "Grid",
                type="button",
                cls="px-3 py-1 rounded-l-lg text-xs transition-all",
                style=_TAB_ACTIVE if view_mode == DecklistViewMode.GRID else _TAB_INACTIVE,
                hx_get=f"{base_url}&view_mode={DecklistViewMode.GRID}",
                hx_target=f"#{container_id}",
                hx_swap="innerHTML",
            ),
            ft.Button(
                ft.I(cls="fas fa-list mr-1"), "List",
                type="button",
                cls="px-3 py-1 rounded-r-lg text-xs transition-all",
                style=_TAB_ACTIVE if view_mode == DecklistViewMode.LIST else _TAB_INACTIVE,
                hx_get=f"{base_url}&view_mode={DecklistViewMode.LIST}",
                hx_target=f"#{container_id}",
                hx_swap="innerHTML",
            ),
            cls="flex items-center"
        )

        decklist_view = display_decklist_modal(
            decklist=selected.decklist,
            card_id2card_data=card_id2card_data,
            leader_id=leader_id,
            view_mode=view_mode,
            unique_id=unique_id,
        )

        return ft.Div(
            ft.Pre(export_str, id=export_pre_id, style="display:none;"),
            ft.Div(
                ft.Div(
                    view_toggle,
                    ft.Span(
                        f"{total_cards} cards · {selected.meta_format}",
                        style="font-size:.75rem;color:#475569;margin-left:.75rem;",
                    ),
                    cls="flex items-center"
                ),
                ft.Div(
                    ft.Button(
                        ft.I(cls="fas fa-copy mr-1"),
                        "Copy for Sim",
                        id=copy_btn_id,
                        type="button",
                        cls="wl-btn-ghost",
                        style="font-size:.75rem;padding:4px 10px;display:inline-flex;align-items:center;margin-right:.5rem;",
                        onclick=f"window._copyDecklistSim('{copy_btn_id}', '{export_pre_id}'); event.stopPropagation();",
                    ),
                    ft.A(
                        ft.I(cls="fas fa-external-link-alt mr-1 text-xs"),
                        "Full view",
                        href=f"/leader?lid={leader_id}&meta_format={selected.meta_format}&modal=decklist&tournament_id={tournament_id}&player_id={player_id}",
                        style="font-size:.75rem;color:#38bdf8;transition:color .15s;display:inline-flex;align-items:center;",
                    ),
                    cls="flex items-center"
                ),
                cls="flex flex-wrap items-center justify-between gap-y-2 mb-3"
            ),
            decklist_view,
            ft.Script("""
(function() {
    if (window._copyDecklistSim) return;
    window._copyDecklistSim = function(btnId, preId) {
        var btn = document.getElementById(btnId);
        var pre = document.getElementById(preId);
        if (!btn || !pre) return;
        var text = pre.textContent;
        var done = function() {
            var orig = btn.innerHTML;
            btn.innerHTML = '<i class="fas fa-check mr-1"></i>Copied!';
            btn.style.background = 'rgba(16,185,129,.15)';
            btn.style.color = '#10b981';
            btn.style.borderColor = 'rgba(16,185,129,.35)';
            setTimeout(function() {
                btn.innerHTML = orig;
                btn.style.background = '';
                btn.style.color = '';
                btn.style.borderColor = '';
            }, 2000);
        };
        if (navigator.clipboard && navigator.clipboard.writeText) {
            navigator.clipboard.writeText(text).then(done).catch(function() { _copyFallback(text, done); });
        } else {
            _copyFallback(text, done);
        }
    };
    function _copyFallback(text, done) {
        var ta = document.createElement('textarea');
        ta.value = text; ta.style.position = 'fixed'; ta.style.left = '-9999px';
        document.body.appendChild(ta); ta.focus(); ta.select();
        try { document.execCommand('copy'); done(); } catch(e) {}
        document.body.removeChild(ta);
    }
})();
"""),
            style="padding:12px 16px 16px;border-top:1px solid #1a2540;"
        )

    @rt("/api/watchlist/custom-decklist/tag-editor", methods=["GET"])
    async def custom_decklist_tag_editor(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        p = request.query_params
        custom_id = p.get('custom_id', '')
        tags = _parse_tags(p.get('tags', DEFAULT_WATCHLIST_TAG))
        return _custom_tag_editor(custom_id, tags)

    @rt("/api/watchlist/custom-decklist/tag-chips", methods=["GET"])
    async def custom_decklist_tag_chips(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        p = request.query_params
        custom_id = p.get('custom_id', '')
        tags = _parse_tags(p.get('tags', DEFAULT_WATCHLIST_TAG))
        return _custom_tag_chips(custom_id, tags)

    @rt("/api/watchlist/custom-decklist/tags", methods=["POST"])
    async def custom_decklist_update_tags(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        form = await request.form()
        custom_id = form.get('custom_id', '')
        tags = _parse_tags(form.get('tags', DEFAULT_WATCHLIST_TAG))
        if not custom_id:
            return JSONResponse({"error": "custom_id required"}, status_code=400)
        update_custom_decklist(user.get('sub'), custom_id, tags=tags)
        return _custom_tag_chips(custom_id, tags)

    @rt("/api/decklist-builder/import-text", methods=["POST"])
    async def builder_import_text(request: Request):
        """Parse pasted decklist text (format: '4xOP01-001') and return card data."""
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)
        text = data.get('text', '')
        card_lookup = get_card_id_card_data_lookup()
        cards = []
        for line in text.splitlines():
            line = line.strip()
            if not line:
                continue
            m = re.match(r'^(\d+)[xX](.+)$', line)
            if not m:
                continue
            count = min(int(m.group(1)), 4)
            card_id = m.group(2).strip()
            c = card_lookup.get(card_id)
            if c:
                cards.append({
                    'id': card_id,
                    'count': count,
                    'name': c.name,
                    'img': c.image_url,
                    'is_leader': c.card_category == OPTcgCardCatagory.LEADER,
                    'colors': [col.value for col in c.colors],
                    'cost': int(c.cost or 0) if c.cost else 0,
                    'type': c.card_category.value,
                    'counter': int(c.counter) if c.counter else 0,
                    'has_trigger': '[Trigger]' in c.ability,
                })
        return JSONResponse(cards)

    # ── Custom decklist builder routes ─────────────────────────────────────

    @rt("/api/decklist-builder/card-search", methods=["GET"])
    async def builder_card_search(request: Request):
        """Card search for the custom decklist builder. Reuses filter_cards logic."""
        from op_tcg.frontend.api.routes.pages import filter_cards

        params = CardPopularityParams(**get_query_params_as_dict(request))
        if not params.search_term:
            return ft.P("Type to search for cards.", style="color:#475569;font-size:.875rem;text-align:center;padding:16px 0;")

        card_lookup = get_card_id_card_data_lookup()
        filtered = filter_cards(list(card_lookup.values()), params)

        if not filtered:
            return ft.P("No cards found.", style="color:#475569;font-size:.875rem;text-align:center;padding:16px 0;")

        # Sort by popularity (same logic as card popularity page)
        popularity_list = get_card_popularity_data()
        popularity_dict: dict[str, float] = {}
        for cp in popularity_list:
            if cp.meta_format == params.meta_format:
                if cp.card_id not in popularity_dict or cp.popularity > popularity_dict[cp.card_id]:
                    popularity_dict[cp.card_id] = cp.popularity
        filtered.sort(key=lambda c: popularity_dict.get(c.id, 0), reverse=True)
        filtered = filtered[:24]

        return ft.Div(
            *[
                ft.Div(
                    ft.Img(src=c.image_url, cls="w-full h-auto block", alt=c.name),
                    ft.Div(
                        ft.Span(c.name, cls="db-card-name-strip"),
                        ft.Span(c.id, cls="db-card-cost-strip"),
                        cls="db-card-info-strip",
                    ),
                    ft.Span("", cls="db-card-count"),
                    *(
                        [ft.Span("♛", cls="db-card-leader-crown")]
                        if c.card_category == OPTcgCardCatagory.LEADER else []
                    ),
                    cls=f"db-card-item{' is-leader' if c.card_category == OPTcgCardCatagory.LEADER else ''}",
                    data_card_id=c.id,
                    data_card_name=c.name,
                    data_card_img=c.image_url,
                    data_is_leader="1" if c.card_category == OPTcgCardCatagory.LEADER else "0",
                    data_card_cost=str(c.cost or 0),
                    data_card_type=c.card_category.value,
                    data_card_counter=str(c.counter or 0),
                    data_card_trigger="1" if '[Trigger]' in c.ability else "0",
                    onclick="if(window._cdb){window._cdb.addFromBtn(this);window._dbCardFlash(this);}",
                )
                for c in filtered
            ],
            cls="db-card-grid"
        )

    @rt("/api/watchlist/custom-decklist/save", methods=["POST"])
    async def custom_decklist_save(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        name = (data.get('name') or '').strip()
        leader_id = data.get('leader_id', '')
        decklist = data.get('decklist') or {}
        custom_id = data.get('custom_id') or None

        if not name or not leader_id:
            return JSONResponse({"error": "name and leader_id are required"}, status_code=400)

        user_id = user.get('sub')
        if custom_id:
            update_custom_decklist(user_id, custom_id, name=name, leader_id=leader_id, decklist=decklist)
        else:
            create_custom_decklist(user_id, name=name, leader_id=leader_id, decklist=decklist)

        return JSONResponse({"status": "success"})

    @rt("/api/watchlist/custom-decklist/delete", methods=["POST"])
    async def custom_decklist_delete(request: Request):
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)
        try:
            data = await request.json()
        except Exception:
            return JSONResponse({"error": "Invalid JSON"}, status_code=400)

        custom_id = data.get('custom_id')
        if not custom_id:
            return JSONResponse({"error": "custom_id required"}, status_code=400)

        delete_custom_decklist(user.get('sub'), custom_id)
        return JSONResponse({"status": "success"})

    @rt("/api/watchlist/custom-decklist/inline-cards", methods=["GET"])
    async def custom_decklist_inline_cards(request: Request):
        """Inline card view for a custom decklist (lazy-loaded on expand)."""
        user = request.session.get('user')
        if not user:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

        custom_id = request.query_params.get('custom_id', '')
        view_mode = request.query_params.get('view_mode', DecklistViewMode.GRID)
        if not custom_id:
            return ft.P("Missing custom_id.", style="color:#ef4444;font-size:.875rem;padding:.75rem;")

        custom = next((d for d in get_custom_decklists(user.get('sub')) if d.get('id') == custom_id), None)
        if not custom or not custom.get('decklist'):
            return ft.P("Decklist not found.", style="color:#475569;font-size:.875rem;padding:.75rem;")

        decklist = {k: int(v) for k, v in custom['decklist'].items()}
        leader_id = custom.get('leader_id', '')
        card_id2card_data = get_card_id_card_data_lookup()
        total_cards = sum(decklist.values())

        safe_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', custom_id)[:20]
        container_id = f"cdl-cards-{safe_id}"
        unique_id = safe_id
        base_url = f"/api/watchlist/custom-decklist/inline-cards?custom_id={custom_id}"

        export_str = decklist_to_export_str(ensure_leader_id(decklist, leader_id))
        copy_btn_id = f"cdl-copy-btn-{safe_id}"
        export_pre_id = f"cdl-export-{safe_id}"

        view_toggle = ft.Div(
            ft.Button(
                ft.I(cls="fas fa-th-large mr-1"), "Grid",
                type="button",
                cls="px-3 py-1 rounded-l-lg text-xs transition-all",
                style=_TAB_ACTIVE if view_mode == DecklistViewMode.GRID else _TAB_INACTIVE,
                hx_get=f"{base_url}&view_mode={DecklistViewMode.GRID}",
                hx_target=f"#{container_id}", hx_swap="innerHTML",
            ),
            ft.Button(
                ft.I(cls="fas fa-list mr-1"), "List",
                type="button",
                cls="px-3 py-1 rounded-r-lg text-xs transition-all",
                style=_TAB_ACTIVE if view_mode == DecklistViewMode.LIST else _TAB_INACTIVE,
                hx_get=f"{base_url}&view_mode={DecklistViewMode.LIST}",
                hx_target=f"#{container_id}", hx_swap="innerHTML",
            ),
            cls="flex items-center"
        )

        return ft.Div(
            ft.Pre(export_str, id=export_pre_id, style="display:none;"),
            ft.Div(
                ft.Div(
                    view_toggle,
                    ft.Span(
                        f"{total_cards} cards",
                        style="font-size:.75rem;color:#475569;margin-left:.75rem;",
                    ),
                    cls="flex items-center"
                ),
                ft.Button(
                    ft.I(cls="fas fa-copy mr-1"),
                    "Copy for Sim",
                    id=copy_btn_id,
                    type="button",
                    cls="wl-btn-ghost",
                    style="font-size:.75rem;padding:4px 10px;display:inline-flex;align-items:center;",
                    onclick=f"window._copyDecklistSim('{copy_btn_id}', '{export_pre_id}'); event.stopPropagation();",
                ),
                cls="flex items-center justify-between mb-3"
            ),
            display_decklist_modal(
                decklist=decklist,
                card_id2card_data=card_id2card_data,
                leader_id=leader_id,
                view_mode=view_mode,
                unique_id=unique_id,
            ),
            style="padding:12px 16px 16px;border-top:1px solid #1a2540;"
        )
