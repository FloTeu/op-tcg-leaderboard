import re
from fasthtml import ft
from op_tcg.backend.db import get_watchlist, get_user_settings, get_decklist_watchlist, get_custom_decklists
from op_tcg.frontend.components.watchlist_toggle import create_watchlist_toggle
from op_tcg.frontend.components.decklist_watchlist_toggle import create_decklist_watchlist_toggle
from op_tcg.frontend.utils.card_price import get_marketplace_link
from op_tcg.frontend.utils.extract import get_card_lookup_by_id_and_aa, get_card_id_card_data_lookup
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.backend.models.cards import CardCurrency


def _qty_stepper(card_id: str, aa_version: int, language: str, quantity: int) -> ft.Div:
    """−/count/+ quantity stepper. JS in _qty_script() handles clicks."""
    return ft.Div(
        ft.Button("−", type="button", cls="qty-btn w-7 h-7 flex items-center justify-center rounded-l bg-gray-700 hover:bg-gray-600 text-white text-base font-bold leading-none transition-colors", data_delta="-1"),
        ft.Span(str(quantity), cls="qty-value w-8 text-center text-white text-sm font-semibold bg-gray-800 h-7 flex items-center justify-center select-none"),
        ft.Button("+", type="button", cls="qty-btn w-7 h-7 flex items-center justify-center rounded-r bg-gray-700 hover:bg-gray-600 text-white text-base font-bold leading-none transition-colors", data_delta="1"),
        cls="qty-stepper flex items-center",
        data_card_id=card_id,
        data_card_version=str(aa_version),
        data_language=language,
    )


def _table_time_range_script() -> ft.Script:
    return ft.Script("""
(function(){
  function updateAllTableCharts(days){
    document.querySelectorAll('.table-chart-container').forEach(function(container){
      var chartId=container.id;
      var loadingEl=document.getElementById(chartId+'-loading');
      var cardId=container.dataset.cardId;
      var aaVersion=container.dataset.aaVersion;
      container.innerHTML='';
      if(loadingEl) loadingEl.classList.remove('hidden');
      fetch('/api/card-price-development-chart?card_id='+cardId+'&days='+days+'&aa_version='+aaVersion+'&compact=true&location=watchlist')
        .then(function(r){return r.text();})
        .then(function(html){
          container.innerHTML=html;
          // innerHTML does not execute scripts — re-run each one manually
          container.querySelectorAll('script').forEach(function(old){
            var s=document.createElement('script');
            s.textContent=old.textContent;
            old.parentNode.replaceChild(s,old);
          });
          if(loadingEl) loadingEl.classList.add('hidden');
        })
        .catch(function(){if(loadingEl) loadingEl.classList.add('hidden');});
    });
  }
  window.updateAllTableCharts=updateAllTableCharts;
})();
""")


def _qty_script() -> ft.Script:
    return ft.Script("""
(function(){
  function init(){
    document.querySelectorAll('.qty-btn').forEach(function(btn){
      if(btn._qi) return; btn._qi=true;
      btn.addEventListener('click', async function(){
        var s=btn.closest('.qty-stepper');
        var d=s.querySelector('.qty-value');
        var cur=parseInt(d.textContent,10);
        var next=Math.max(1,cur+parseInt(btn.dataset.delta,10));
        if(next===cur) return;
        d.textContent=next;
        // update nearest price spans
        var card=s.closest('[data-eur-price]');
        if(card){
          var eur=parseFloat(card.dataset.eurPrice);
          var usd=parseFloat(card.dataset.usdPrice);
          card.querySelectorAll('[data-price-eur]').forEach(function(el){el.textContent='€'+(eur*next).toFixed(2);});
          card.querySelectorAll('[data-price-usd]').forEach(function(el){el.textContent='$'+(usd*next).toFixed(2);});
        }
        await fetch('/api/watchlist/quantity',{method:'POST',headers:{'Content-Type':'application/json'},
          body:JSON.stringify({card_id:s.dataset.cardId,card_version:parseInt(s.dataset.cardVersion,10),language:s.dataset.language,quantity:next})});
      });
    });
  }
  document.addEventListener('DOMContentLoaded',init);
  document.addEventListener('htmx:afterSwap',init);
})();
""")


def _decklist_watchlist_section(user_id: str, request) -> ft.Div:
    """Renders the saved decklists section of the watchlist page."""
    dl_watchlist = get_decklist_watchlist(user_id)
    card_lookup = get_card_id_card_data_lookup()  # flat: card_id -> ExtendedCardData (aa_version=0)

    tag_filter = request.query_params.get("tag", "")
    custom_decklists_all = get_custom_decklists(user_id)
    all_tags = sorted({tag for item in dl_watchlist for tag in item.get('tags', ['my decklists'])} |
                      {tag for item in custom_decklists_all for tag in item.get('tags', ['my decklists'])})

    if tag_filter:
        dl_watchlist = [item for item in dl_watchlist if tag_filter in item.get('tags', ['my decklists'])]
        custom_decklists_all = [item for item in custom_decklists_all if tag_filter in item.get('tags', ['my decklists'])]

    def build_url(tag=None):
        t = tag if tag is not None else tag_filter
        params = "section=decklists"
        if t:
            params += f"&tag={t}"
        return f"?{params}"

    tag_filter_bar = ft.Div(
        ft.A("All", href=build_url(tag=""),
             cls=f"px-3 py-1 rounded-full text-xs font-medium transition-colors mr-1 mb-1 {'bg-blue-600 text-white' if not tag_filter else 'bg-gray-700 text-gray-300 hover:bg-gray-600'}"),
        *[
            ft.A(tag, href=build_url(tag=tag),
                 cls=f"px-3 py-1 rounded-full text-xs font-medium transition-colors mr-1 mb-1 {'bg-blue-600 text-white' if tag_filter == tag else 'bg-gray-700 text-gray-300 hover:bg-gray-600'}")
            for tag in all_tags
        ],
        cls="flex flex-wrap items-center mb-4"
    ) if all_tags else ft.Span()

    if not dl_watchlist and not custom_decklists_all:
        return ft.Div(
            tag_filter_bar,
            ft.Div(
                ft.I(cls="fas fa-layer-group text-4xl text-gray-600 mb-3"),
                ft.P("No saved decklists yet.", cls="text-gray-400 text-sm"),
                ft.P("Open a tournament decklist and click the heart icon to save it.", cls="text-gray-500 text-xs mt-1"),
                cls="flex flex-col items-center justify-center py-16 text-center"
            ),
        )

    items = []
    for i, item in enumerate(dl_watchlist):
        leader_id = item.get('leader_id', '')
        tournament_id = item.get('tournament_id', '')
        player_id = item.get('player_id', '')
        meta_format = item.get('meta_format', '')
        tags = item.get('tags', ['my decklists']) or ['my decklists']

        leader_data = card_lookup.get(leader_id)
        image_url = getattr(leader_data, 'image_url', '') if leader_data else ''
        leader_name = getattr(leader_data, 'name', leader_id) if leader_data else leader_id
        tournament_ts = item.get('tournament_timestamp')
        tournament_date_str = tournament_ts.strftime('%-d %b %Y') if tournament_ts else ''

        safe_tid = re.sub(r'[^a-zA-Z0-9_\-]', '_', tournament_id)[:20]
        safe_pid = re.sub(r'[^a-zA-Z0-9_\-]', '_', player_id)[:20]
        tag_target_id = f"tags-dl-{leader_id}-{safe_tid}-{safe_pid}"
        tags_str = ",".join(tags)

        tag_chips = ft.Div(
            *[ft.Span(tag, cls="inline-block bg-blue-600/30 text-blue-300 text-xs px-2 py-0.5 rounded-full mr-1") for tag in tags],
            ft.Button(
                ft.I(cls="fas fa-pen text-xs"),
                type="button",
                cls="text-gray-600 hover:text-gray-300 ml-1 transition-colors",
                title="Edit tags",
                hx_get=f"/api/watchlist/decklist/tag-editor?leader_id={leader_id}&tournament_id={tournament_id}&player_id={player_id}&tags={tags_str}",
                hx_target=f"#{tag_target_id}",
                hx_swap="outerHTML",
            ),
            id=tag_target_id,
            cls="flex flex-wrap items-center mt-1",
            onclick="event.stopPropagation();"
        )

        toggle_btn = create_decklist_watchlist_toggle(
            leader_id=leader_id,
            tournament_id=tournament_id,
            player_id=player_id,
            meta_format=meta_format,
            is_in_watchlist=True,
            include_script=(i == 0),
        )

        cards_container_id = f"dl-cards-{leader_id}-{safe_tid}-{safe_pid}"
        expand_btn_id = f"dl-expand-btn-{leader_id}-{safe_tid}-{safe_pid}"
        cards_url = f"/api/watchlist/decklist/inline-cards?leader_id={leader_id}&tournament_id={tournament_id}&player_id={player_id}&view_mode=grid"

        items.append(
            ft.Div(
                # Header row
                ft.Div(
                    # Leader card thumbnail
                    ft.Div(
                        ft.Img(src=image_url, cls="w-14 sm:w-16 h-auto rounded shadow-sm", alt=leader_name) if image_url else ft.Div(cls="w-14 sm:w-16 h-20 bg-gray-700 rounded"),
                        cls="flex-shrink-0 mr-4"
                    ),
                    # Info
                    ft.Div(
                        ft.Div(
                            ft.Span(leader_id, cls="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-yellow-500/20 text-yellow-300 border border-yellow-500/30"),
                            ft.Span(leader_name, cls="text-white font-bold text-sm sm:text-base"),
                            *(
                                [ft.Span(meta_format, cls="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium bg-blue-500/20 text-blue-300 border border-blue-500/30")]
                                if meta_format else []
                            ),
                            cls="flex items-center flex-wrap gap-2 mb-1"
                        ),
                        ft.P(f"Player: {player_id}", cls="text-xs text-gray-400 truncate"),
                        ft.P(f"Tournament: {tournament_id[:40]}{'...' if len(tournament_id) > 40 else ''}", cls="text-xs text-gray-500 truncate"),
                        *(
                            [ft.P(f"Played: {tournament_date_str}", cls="text-xs text-gray-500")]
                            if tournament_date_str else []
                        ),
                        tag_chips,
                        cls="flex-1 min-w-0"
                    ),
                    # Actions
                    ft.Div(
                        toggle_btn,
                        cls="flex flex-col items-end flex-shrink-0 ml-2"
                    ),
                    cls="flex items-start px-4 py-4",
                ),
                # Expand/collapse footer
                ft.Button(
                    ft.I(cls="fas fa-chevron-down mr-2 text-xs transition-transform", id=f"{expand_btn_id}-icon"),
                    "Show cards",
                    id=expand_btn_id,
                    type="button",
                    cls="w-full flex items-center justify-center text-xs text-gray-400 hover:text-white hover:bg-gray-700/40 transition-colors py-2 border-t border-gray-700/60",
                    onclick=f"toggleDecklistCards('{expand_btn_id}', '{cards_container_id}')",
                ),
                # Lazy-loaded cards area (hidden until expanded)
                ft.Div(
                    create_loading_spinner(id=f"{cards_container_id}-loading", size="w-5 h-5", container_classes="flex items-center justify-center py-6 hidden"),
                    id=cards_container_id,
                    cls="hidden",
                    hx_get=cards_url,
                    hx_trigger="expand once",
                    hx_swap="innerHTML",
                    hx_indicator=f"#{cards_container_id}-loading",
                ),
                cls="decklist-watchlist-item bg-gray-800/60 border border-gray-700 rounded-xl overflow-hidden",
            )
        )

    toggle_script = ft.Script("""
(function() {
    if (window.toggleDecklistCards) return;
    window.toggleDecklistCards = function(btnId, containerId) {
        const btn = document.getElementById(btnId);
        const container = document.getElementById(containerId);
        const icon = document.getElementById(btnId + '-icon');
        if (!btn || !container) return;
        const isHidden = container.classList.contains('hidden');
        if (isHidden) {
            container.classList.remove('hidden');
            if (icon) icon.style.transform = 'rotate(180deg)';
            btn.querySelector('span') && (btn.lastChild.textContent = ' Hide cards');
            // Replace text node
            btn.childNodes.forEach(function(n) { if (n.nodeType === 3 && n.textContent.trim()) n.textContent = ' Hide cards'; });
            if (!container.dataset.loaded) {
                container.dataset.loaded = '1';
                htmx.trigger(container, 'expand');
            }
        } else {
            container.classList.add('hidden');
            if (icon) icon.style.transform = '';
            btn.childNodes.forEach(function(n) { if (n.nodeType === 3 && n.textContent.trim()) n.textContent = ' Show cards'; });
        }
    };
})();
""")

    # ── Custom decklists subsection ─────────────────────────────────────
    custom_items = []
    for ci, custom in enumerate(custom_decklists_all):
        custom_id = custom.get('id', '')
        c_leader_id = custom.get('leader_id', '')
        c_name = custom.get('name', 'Unnamed')
        c_decklist = custom.get('decklist') or {}
        c_card_count = sum(int(v) for v in c_decklist.values())
        c_tags = custom.get('tags', ['my decklists']) or ['my decklists']

        c_leader_data = card_lookup.get(c_leader_id)
        c_image_url = getattr(c_leader_data, 'image_url', '') if c_leader_data else ''
        c_leader_name = getattr(c_leader_data, 'name', c_leader_id) if c_leader_data else c_leader_id

        safe_cid = re.sub(r'[^a-zA-Z0-9_\-]', '_', custom_id)[:20]
        c_cards_id = f"cdl-cards-{safe_cid}"
        c_expand_btn_id = f"cdl-expand-btn-{safe_cid}"
        c_cards_url = f"/api/watchlist/custom-decklist/inline-cards?custom_id={custom_id}&view_mode=grid"
        c_tag_target_id = f"tags-cdl-{safe_cid}"
        c_tags_str = ",".join(c_tags)

        c_tag_chips = ft.Div(
            *[ft.Span(tag, cls="inline-block bg-purple-600/30 text-purple-300 text-xs px-2 py-0.5 rounded-full mr-1") for tag in c_tags],
            ft.Button(
                ft.I(cls="fas fa-pen text-xs"),
                type="button",
                cls="text-gray-600 hover:text-gray-300 ml-1 transition-colors",
                title="Edit tags",
                hx_get=f"/api/watchlist/custom-decklist/tag-editor?custom_id={custom_id}&tags={c_tags_str}",
                hx_target=f"#{c_tag_target_id}",
                hx_swap="outerHTML",
            ),
            id=c_tag_target_id,
            cls="flex flex-wrap items-center mt-1",
            onclick="event.stopPropagation();"
        )

        custom_items.append(
            ft.Div(
                ft.Div(
                    ft.Div(
                        ft.Img(src=c_image_url, cls="w-14 sm:w-16 h-auto rounded shadow-sm", alt=c_leader_name) if c_image_url else ft.Div(cls="w-14 sm:w-16 h-20 bg-gray-700 rounded"),
                        cls="flex-shrink-0 mr-4"
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span("Custom", cls="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-semibold bg-purple-500/20 text-purple-300 border border-purple-500/30"),
                            ft.Span(c_name, cls="text-white font-bold text-sm sm:text-base"),
                            cls="flex items-center flex-wrap gap-2 mb-1"
                        ),
                        ft.P(f"Leader: {c_leader_name}", cls="text-xs text-gray-400"),
                        ft.P(f"{c_card_count} cards", cls="text-xs text-gray-500"),
                        c_tag_chips,
                        cls="flex-1 min-w-0"
                    ),
                    ft.Div(
                        ft.Button(
                            ft.I(cls="fas fa-pen text-xs"),
                            type="button",
                            cls="w-8 h-8 flex items-center justify-center rounded-full bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors",
                            title="Edit decklist",
                            hx_get=f"/api/watchlist/custom-decklist/builder?custom_id={custom_id}",
                            hx_target="#decklist-builder-wrapper",
                            hx_swap="innerHTML",
                            onclick="document.getElementById('decklist-builder-wrapper').classList.remove('hidden'); document.getElementById('decklist-builder-wrapper').scrollIntoView({behavior:'smooth'});",
                        ),
                        ft.Button(
                            ft.I(cls="fas fa-trash text-xs"),
                            type="button",
                            cls="w-8 h-8 flex items-center justify-center rounded-full bg-gray-700 hover:bg-red-700 text-gray-300 hover:text-white transition-colors mt-1",
                            title="Delete",
                            onclick=f"if(confirm('Delete \"{c_name}\"?')) fetch('/api/watchlist/custom-decklist/delete',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{custom_id:'{custom_id}'}})}})" +
                                    f".then(r=>r.ok && this.closest('.decklist-watchlist-item').remove());",
                        ),
                        cls="flex flex-col items-end flex-shrink-0 ml-2"
                    ),
                    cls="flex items-start px-4 py-4",
                ),
                ft.Button(
                    ft.I(cls="fas fa-chevron-down mr-2 text-xs transition-transform", id=f"{c_expand_btn_id}-icon"),
                    "Show cards",
                    id=c_expand_btn_id,
                    type="button",
                    cls="w-full flex items-center justify-center text-xs text-gray-400 hover:text-white hover:bg-gray-700/40 transition-colors py-2 border-t border-gray-700/60",
                    onclick=f"toggleDecklistCards('{c_expand_btn_id}', '{c_cards_id}')",
                ),
                ft.Div(
                    create_loading_spinner(id=f"{c_cards_id}-loading", size="w-5 h-5", container_classes="flex items-center justify-center py-6 hidden"),
                    id=c_cards_id,
                    cls="hidden",
                    hx_get=c_cards_url,
                    hx_trigger="expand once",
                    hx_swap="innerHTML",
                    hx_indicator=f"#{c_cards_id}-loading",
                ),
                cls="decklist-watchlist-item bg-gray-800/60 border border-purple-900/40 rounded-xl overflow-hidden",
            )
        )

    return ft.Div(
        toggle_script,
        # Builder wrapper (hidden until "Create" is clicked or edit is triggered)
        ft.Div(
            id="decklist-builder-wrapper",
            cls="hidden",
            hx_get="/api/watchlist/custom-decklist/builder",
            hx_trigger="open-builder",
            hx_swap="innerHTML",
        ),
        # Create button + tag filter bar
        ft.Div(
            tag_filter_bar,
            ft.Button(
                ft.I(cls="fas fa-plus mr-2"),
                "Create Decklist",
                type="button",
                cls="px-3 py-1.5 text-xs font-medium bg-purple-600 hover:bg-purple-500 text-white rounded-lg transition-colors inline-flex items-center flex-shrink-0",
                onclick="""
                    var w = document.getElementById('decklist-builder-wrapper');
                    w.classList.remove('hidden');
                    if (!w.innerHTML.trim()) {
                        w.addEventListener('htmx:afterSwap', function() {
                            w.scrollIntoView({behavior:'smooth'});
                        }, {once: true});
                        htmx.trigger(w, 'open-builder');
                    } else {
                        w.scrollIntoView({behavior:'smooth'});
                    }
                """,
            ),
            cls="flex items-start justify-between gap-3 mb-4"
        ),
        # Custom decklists (if any)
        *(
            [ft.Div(
                ft.P("Custom Decklists", cls="text-xs font-semibold text-purple-300 uppercase tracking-wider mb-2"),
                ft.Div(*custom_items, cls="grid grid-cols-1 gap-4 mb-6"),
            )] if custom_items else []
        ),
        # Tournament decklists
        *(
            [ft.Div(
                ft.P("Watchlist Decklists", cls="text-xs font-semibold text-purple-300 uppercase tracking-wider mb-2"),
                ft.Div(*items, cls="grid grid-cols-1 gap-4"),
            )] if items else []
        ),
    )


def watchlist_page(request):
    user = request.session.get('user')
    if not user:
         return ft.Div(
             ft.H1("Access Denied", cls="text-2xl font-bold text-white mb-4"),
             ft.P("Please login to view your watchlist.", cls="text-gray-400"),
             cls="container mx-auto px-4 py-8"
         )

    user_id = user.get('sub')
    section = request.query_params.get("section", "cards")

    # Section switcher shown in all states
    section_switcher = ft.Div(
        ft.A(
            ft.I(cls="fas fa-clone mr-2"),
            "Cards",
            href="?section=cards",
            cls=f"px-4 py-2 rounded-l-lg border border-gray-600 {'bg-blue-600 text-white' if section == 'cards' else 'bg-gray-800 text-gray-400 hover:bg-gray-700'} flex items-center transition-colors text-sm font-medium"
        ),
        ft.A(
            ft.I(cls="fas fa-layer-group mr-2"),
            "Decklists",
            href="?section=decklists",
            cls=f"px-4 py-2 rounded-r-lg border border-gray-600 border-l-0 {'bg-blue-600 text-white' if section == 'decklists' else 'bg-gray-800 text-gray-400 hover:bg-gray-700'} flex items-center transition-colors text-sm font-medium"
        ),
        cls="flex items-center"
    )

    if section == 'decklists':
        return ft.Div(
            ft.Div(
                ft.H1("My Watchlist", cls="text-2xl font-bold text-white"),
                section_switcher,
                cls="flex flex-wrap justify-between items-center gap-y-3 mb-6"
            ),
            _decklist_watchlist_section(user_id, request),
            cls="container mx-auto px-4 py-8"
        )

    watchlist = get_watchlist(user_id)

    if not watchlist:
        return ft.Div(
            ft.Div(
                ft.H1("My Watchlist", cls="text-2xl font-bold text-white"),
                section_switcher,
                cls="flex flex-wrap justify-between items-center gap-y-3 mb-6"
            ),
            ft.P("Your card watchlist is currently empty.", cls="text-gray-400"),
            cls="container mx-auto px-4 py-8"
        )

    # Get all card data to lookup details
    # Use nested lookup to find specific version details (image, name, etc.)
    card_lookup = get_card_lookup_by_id_and_aa()

    # Determine View Mode
    view_mode = request.query_params.get("view", "list")
    sort_by = request.query_params.get("sort", "name")
    sort_order = request.query_params.get("order", "asc")
    tag_filter = request.query_params.get("tag", "")

    # Collect all unique tags for filter bar (before filtering)
    all_tags = sorted({tag for item in watchlist for tag in item.get('tags', ['my collection'])})

    # Filter by tag if active
    if tag_filter:
        watchlist = [item for item in watchlist if tag_filter in item.get('tags', ['my collection'])]

    def build_url(view=None, sort=None, order=None, tag=None):
        v = view or view_mode
        s = sort or sort_by
        o = order or sort_order
        t = tag if tag is not None else tag_filter
        params = f"view={v}&sort={s}&order={o}"
        if t:
            params += f"&tag={t}"
        return f"?{params}"

    # Prepare data for rendering (needed for both views to support sorting/prices)
    prepared_items = []

    for item in watchlist:
        card_id = item.get('card_id')
        version_val = item.get('card_version', 0)
        try:
             aa_version = int(version_val) if version_val != 'Base' else 0
        except:
             aa_version = 0
        language = item.get('language', 'en')

        # Data Lookup
        card_details = None
        if card_id in card_lookup:
            card_details = card_lookup[card_id].get(aa_version)
            if not card_details:
                card_details = card_lookup[card_id].get(0)
                if not card_details and card_lookup[card_id]:
                        card_details = next(iter(card_lookup[card_id].values()))

        card_name = getattr(card_details, 'name', 'Unknown Card') if card_details else card_id
        image_url = getattr(card_details, 'image_url', '') if card_details else ''
        latest_eur = getattr(card_details, 'latest_eur_price', 0.0) if card_details else 0.0
        latest_usd = getattr(card_details, 'latest_usd_price', 0.0) if card_details else 0.0

        # Ensure prices are floats
        if latest_eur is None: latest_eur = 0.0
        if latest_usd is None: latest_usd = 0.0

        tags = item.get('tags', ['my collection'])
        if not tags:
            tags = ['my collection']
        quantity = max(1, int(item.get('quantity', 1)))

        item_data = {
            'card_id': card_id,
            'aa_version': aa_version,
            'language': language,
            'quantity': quantity,
            'card_details': card_details,
            'card_name': card_name,
            'image_url': image_url,
            'latest_eur': latest_eur,
            'latest_usd': latest_usd,
            'tags': tags,
        }
        prepared_items.append(item_data)

    # Totals for portfolio summary — weighted by quantity
    total_eur = sum(item['latest_eur'] * item['quantity'] for item in prepared_items)
    total_usd = sum(item['latest_usd'] * item['quantity'] for item in prepared_items)
    total_copies = sum(item['quantity'] for item in prepared_items)
    card_count = len(prepared_items)

    # Sort items
    reverse = (sort_order == 'desc')
    if sort_by == 'price':
        user_settings = get_user_settings(user_id)
        price_key = 'latest_eur' if user_settings.get('currency') == CardCurrency.EURO else 'latest_usd'
        prepared_items.sort(key=lambda x: x[price_key], reverse=reverse)
    else: # name
        prepared_items.sort(key=lambda x: x['card_name'], reverse=reverse)

    # Create View Switcher
    view_switcher = ft.Div(
        ft.A(
            ft.I(cls="fas fa-th-large mr-2"),
            "Grid",
            href=build_url(view="list"),
            cls=f"px-4 py-2 rounded-l-lg border border-gray-600 {'bg-blue-600 text-white' if view_mode == 'list' else 'bg-gray-800 text-gray-400 hover:bg-gray-700'} flex items-center transition-colors text-sm font-medium"
        ),
        ft.A(
            ft.I(cls="fas fa-table mr-2"),
            "Table",
            href=build_url(view="table"),
            cls=f"px-4 py-2 rounded-r-lg border border-gray-600 border-l-0 {'bg-blue-600 text-white' if view_mode == 'table' else 'bg-gray-800 text-gray-400 hover:bg-gray-700'} flex items-center transition-colors text-sm font-medium"
        ),
        cls="flex items-center"
    )

    # Tag filter bar
    tag_filter_bar = ft.Div(
        ft.A(
            "All",
            href=build_url(tag=""),
            cls=f"px-3 py-1 rounded-full text-xs font-medium transition-colors mr-1 mb-1 {'bg-blue-600 text-white' if not tag_filter else 'bg-gray-700 text-gray-300 hover:bg-gray-600'}"
        ),
        *[
            ft.A(
                tag,
                href=build_url(tag=tag),
                cls=f"px-3 py-1 rounded-full text-xs font-medium transition-colors mr-1 mb-1 {'bg-blue-600 text-white' if tag_filter == tag else 'bg-gray-700 text-gray-300 hover:bg-gray-600'}"
            )
            for tag in all_tags
        ],
        cls="flex flex-wrap items-center mb-4"
    ) if all_tags else ft.Span()

    content = None

    if view_mode == 'table':
        # Helpers for sort links
        def sort_link(label, column):
            if sort_by == column:
                if sort_order == "asc":
                    icon = "fa-sort-up"
                    new_order = "desc"
                else:
                    icon = "fa-sort-down"
                    new_order = "asc"
                link_cls = "flex items-center cursor-pointer transition-colors text-white"
            else:
                icon = "fa-sort opacity-50"
                new_order = "asc"
                link_cls = "flex items-center cursor-pointer transition-colors hover:text-white text-gray-400"

            return ft.A(
                ft.Span(label),
                ft.I(cls=f"fas {icon} ml-1"),
                href=build_url(view="table", sort=column, order=new_order),
                cls=link_cls
            )

        # Render Table View
        rows = []
        for item in prepared_items:
            card_id = item['card_id']
            aa_version = item['aa_version']
            language = item['language']
            quantity = item['quantity']
            card_details = item['card_details']
            card_name = item['card_name']
            image_url = item['image_url']
            tags = item['tags']

            # Marketplace Links
            if card_details:
                cm_url, _ = get_marketplace_link(card_details, CardCurrency.EURO)
                tcg_url, _ = get_marketplace_link(card_details, CardCurrency.US_DOLLAR)
            else:
                cm_url = f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={card_id}"
                tcg_url = f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={card_id}"

            version_label = "Base" if aa_version == 0 else f"Alt Art {aa_version}"
            tags_str = ",".join(tags)
            tag_target_id = f"tags-{card_id}-{aa_version}-{language}"
            tag_chips = ft.Div(
                *[ft.Span(tag, cls="inline-block bg-blue-600/30 text-blue-300 text-xs px-2 py-0.5 rounded-full mr-1") for tag in tags],
                ft.Button(
                    ft.I(cls="fas fa-pen text-xs"),
                    type="button",
                    cls="text-gray-600 hover:text-gray-300 ml-1 transition-colors",
                    title="Edit tags",
                    hx_get=f"/api/watchlist/tag-editor?card_id={card_id}&card_version={aa_version}&language={language}&tags={tags_str}",
                    hx_target=f"#{tag_target_id}",
                    hx_swap="outerHTML",
                ),
                id=tag_target_id,
                cls="flex flex-wrap items-center mt-1",
                onclick="event.stopPropagation();"
            )

            chart_id = f"chart-table-{card_id}-{aa_version}-{language}"

            toggle_btn = create_watchlist_toggle(
                card_id=card_id,
                card_version=aa_version,
                language=language,
                is_in_watchlist=True,
                include_script=(len(rows) == 0),
                btn_cls="bg-transparent hover:bg-gray-700 p-2 rounded-full"
            )

            rows.append(
                ft.Tr(
                    # Card Info
                    ft.Td(
                        ft.Div(
                            ft.Img(src=image_url, cls="w-16 h-auto rounded shadow-sm mr-4 cursor-pointer hover:opacity-80 transition-opacity flex-shrink-0",
                                   alt=card_name,
                                   hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                   hx_target="body",
                                   hx_swap="beforeend"),
                            ft.Div(
                                ft.Div(card_name, cls="font-bold text-white text-base cursor-pointer hover:text-blue-400 whitespace-normal break-words line-clamp-2",
                                       hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                       hx_target="body",
                                       hx_swap="beforeend"),
                                ft.Div(f"{card_id}", cls="text-sm text-gray-400"),
                                tag_chips,
                                cls="flex flex-col min-w-0"
                            ),
                            cls="flex items-center"
                        ),
                        cls="px-5 py-4 align-top"
                    ),
                    # Latest Price (× quantity)
                    ft.Td(
                        ft.Div(
                            ft.A(
                                ft.Span(f"€{item['latest_eur'] * quantity:.2f}", cls="font-bold text-white group-hover:text-green-300 transition-colors mr-2 text-sm font-mono tabular-nums", data_price_eur=True),
                                ft.Span("CM", cls="text-[10px] bg-green-700/40 text-green-300 group-hover:bg-green-600 group-hover:text-white px-1.5 py-0.5 rounded transition-colors"),
                                href=cm_url,
                                target="_blank",
                                cls="flex items-center justify-end group cursor-pointer hover:bg-green-900/20 rounded px-2 py-1 transition-colors mb-1 w-full"
                            ),
                            ft.A(
                                ft.Span(f"${item['latest_usd'] * quantity:.2f}", cls="font-bold text-white group-hover:text-blue-300 transition-colors mr-2 text-sm font-mono tabular-nums", data_price_usd=True),
                                ft.Span("TCG", cls="text-[10px] bg-blue-700/40 text-blue-300 group-hover:bg-blue-600 group-hover:text-white px-1.5 py-0.5 rounded transition-colors"),
                                href=tcg_url,
                                target="_blank",
                                cls="flex items-center justify-end group cursor-pointer hover:bg-blue-900/20 rounded px-2 py-1 transition-colors w-full"
                            ),
                            cls="flex flex-col items-end min-w-[100px]"
                        ),
                        cls="px-5 py-4 whitespace-nowrap align-middle"
                    ),
                    # Details
                    ft.Td(
                        ft.Div(
                            ft.Div(version_label, cls="text-sm text-gray-300"),
                            ft.Div(language, cls="text-xs text-gray-500 uppercase"),
                            cls="flex flex-col"
                        ),
                        cls="px-5 py-4 whitespace-nowrap align-middle"
                    ),
                    # Quantity
                    ft.Td(
                        _qty_stepper(card_id, aa_version, language, quantity),
                        cls="px-5 py-4 whitespace-nowrap align-middle",
                    ),
                    # Actions
                    ft.Td(
                        ft.Div(
                            toggle_btn,
                            cls="flex items-center justify-center pl-2"
                        ),
                        cls="px-5 py-4 whitespace-nowrap align-middle"
                    ),
                    # Price Chart
                    ft.Td(
                        ft.Div(
                            ft.Div(
                                id=chart_id,
                                hx_get=f"/api/card-price-development-chart?card_id={card_id}&days=90&aa_version={aa_version}&compact=true&location=watchlist",
                                hx_trigger="revealed",
                                hx_indicator=f"#{chart_id}-loading",
                                cls="w-full h-36 table-chart-container",
                                data_card_id=card_id,
                                data_aa_version=str(aa_version),
                            ),
                            create_loading_spinner(
                                id=f"{chart_id}-loading",
                                size="w-6 h-6",
                                container_classes="absolute inset-0 flex items-center justify-center pointer-events-none hidden"
                            ),
                            cls="w-full min-w-[200px] h-36 relative overflow-hidden"
                        ),
                        cls="px-5 py-4 w-full align-middle"
                    ),
                    cls="bg-transparent hover:bg-gray-700/20 transition-colors watchlist-card-item",
                    data_eur_price=str(item['latest_eur']),
                    data_usd_price=str(item['latest_usd']),
                )
            )

        content = ft.Div(
            ft.Table(
                ft.Thead(
                    ft.Tr(
                        ft.Th(sort_link("Card", "name"), cls="px-5 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-widest w-1/3 min-w-[250px]"),
                        ft.Th(sort_link("Price", "price"), cls="px-5 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-widest whitespace-nowrap w-28"),
                        ft.Th("Version", cls="px-5 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-widest whitespace-nowrap w-24"),
                        ft.Th("Qty", cls="px-5 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-widest w-24"),
                        ft.Th("Actions", cls="px-5 py-4 text-left text-xs font-medium text-gray-500 uppercase tracking-widest w-24"),
                        ft.Th(
                            ft.Div(
                                ft.Span("Price Trend", cls="text-xs font-medium text-gray-500 uppercase tracking-widest"),
                                ft.Select(
                                    ft.Option("30d", value="30"),
                                    ft.Option("90d", value="90", selected=True),
                                    ft.Option("180d", value="180"),
                                    ft.Option("1y", value="365"),
                                    ft.Option("All", value="1000"),
                                    id="table-global-time-range",
                                    cls="bg-gray-800 text-white border border-gray-600 rounded px-2 py-0.5 text-xs focus:outline-none focus:border-blue-500 cursor-pointer hover:bg-gray-700 transition-colors",
                                    onchange="updateAllTableCharts(this.value)"
                                ),
                                cls="flex items-center gap-3"
                            ),
                            cls="px-5 py-4 text-left min-w-[300px]"
                        ),
                    ),
                    cls="bg-gray-800/60 border-b border-gray-700/60"
                ),
                ft.Tbody(
                    *rows,
                    cls="divide-y divide-gray-700/60"
                ),
                cls="min-w-full"
            ),
            cls="overflow-x-auto rounded-xl border border-gray-700 overflow-hidden"
        )

    else:
        # LIST VIEW (Existing Logic)
        items = []
        for item in prepared_items:
            card_id = item['card_id']
            aa_version = item['aa_version']
            language = item['language']
            quantity = item['quantity']
            card_details = item['card_details']
            card_name = item['card_name']
            image_url = item['image_url']
            tags = item['tags']

            # Generate marketplace links
            if card_details:
                cm_url, _ = get_marketplace_link(card_details, CardCurrency.EURO)
                tcg_url, _ = get_marketplace_link(card_details, CardCurrency.US_DOLLAR)
            else:
                cm_url = f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={card_id}"
                tcg_url = f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={card_id}"

            # Determine label for version
            version_label = "Base" if aa_version == 0 else f"Alt Art {aa_version}"

            # Create unique ID for chart container
            chart_id = f"chart-{card_id}-{aa_version}-{language}"

            tags_str = ",".join(tags)
            tag_target_id = f"tags-{card_id}-{aa_version}-{language}"
            tag_chips = ft.Div(
                *[ft.Span(tag, cls="inline-block bg-blue-600/30 text-blue-300 text-xs px-2 py-0.5 rounded-full mr-1") for tag in tags],
                ft.Button(
                    ft.I(cls="fas fa-pen text-xs"),
                    type="button",
                    cls="text-gray-600 hover:text-gray-300 ml-1 transition-colors",
                    title="Edit tags",
                    hx_get=f"/api/watchlist/tag-editor?card_id={card_id}&card_version={aa_version}&language={language}&tags={tags_str}",
                    hx_target=f"#{tag_target_id}",
                    hx_swap="outerHTML",
                ),
                id=tag_target_id,
                cls="flex flex-wrap items-center mt-1",
                onclick="event.stopPropagation();"
            )

            toggle_btn = create_watchlist_toggle(
                card_id=card_id,
                card_version=aa_version,
                language=language,
                is_in_watchlist=True,
                include_script=(len(items) == 0)
            )

            items.append(
                ft.Div(
                    # Header section: Image + Details + Toggle
                    ft.Div(
                        ft.Div(
                            ft.Img(src=image_url, cls="w-16 sm:w-20 h-auto rounded shadow-sm hover:opacity-90 transition-opacity",
                                   alt=card_name),
                            cls="flex-shrink-0 mr-4 cursor-pointer",
                            hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                            hx_target="body",
                            hx_swap="beforeend"
                        ),
                        ft.Div(
                            ft.H3(card_name, cls="text-base font-bold text-white hover:text-blue-400 transition-colors leading-snug"),
                            ft.P(f"{card_id} · {version_label} · {language.upper()}", cls="text-xs text-gray-500 mt-0.5 uppercase tracking-wide"),
                            ft.Div(
                                ft.Span(f"€{item['latest_eur'] * quantity:.2f}", cls="text-sm font-bold text-white font-mono tabular-nums mr-3", data_price_eur=True),
                                ft.Span(f"${item['latest_usd'] * quantity:.2f}", cls="text-sm font-bold text-gray-400 font-mono tabular-nums", data_price_usd=True),
                                cls="mt-1.5"
                            ),
                            tag_chips,
                            cls="flex-1 min-w-0 cursor-pointer",
                            hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                            hx_target="body",
                            hx_swap="beforeend"
                        ),
                        ft.Div(toggle_btn, cls="flex-shrink-0 ml-2"),
                        cls="flex items-start px-5 py-4 border-b border-gray-700/60",
                    ),
                    # Quantity row
                    ft.Div(
                        ft.Span("Qty:", cls="text-xs text-gray-500 mr-2"),
                        _qty_stepper(card_id, aa_version, language, quantity),
                        cls="flex items-center px-5 py-2 border-b border-gray-700/60"
                    ),
                    # Chart section
                    ft.Div(
                        ft.Div(
                            ft.Span("Price Trend", cls="text-xs text-gray-500 uppercase tracking-widest font-medium"),
                            ft.Select(
                                ft.Option("30 Days", value="30"),
                                ft.Option("90 Days", value="90", selected=True),
                                ft.Option("180 Days", value="180"),
                                ft.Option("1 Year", value="365"),
                                ft.Option("All Time", value="1000"),
                                name="days",
                                id=f"price-period-selector-{chart_id}",
                                cls="bg-gray-800 text-white border border-gray-600 rounded px-2 py-0.5 text-xs focus:outline-none focus:border-blue-500 cursor-pointer hover:bg-gray-700 transition-colors",
                                hx_get="/api/card-price-development-chart",
                                hx_target=f"#{chart_id}",
                                hx_indicator=f"#{chart_id}-loading",
                                hx_vals=f'{{"card_id": "{card_id}", "aa_version": "{aa_version}", "include_alt_art": "false", "location": "watchlist"}}',
                                hx_on__before_request=f"document.getElementById('{chart_id}').innerHTML = ''; document.getElementById('{chart_id}-loading').classList.remove('hidden');"
                            ),
                            cls="flex items-center justify-between mb-3"
                        ),
                        ft.Div(
                            ft.Div(
                                id=chart_id,
                                hx_get=f"/api/card-price-development-chart?card_id={card_id}&days=90&aa_version={aa_version}&location=watchlist",
                                hx_trigger="revealed",
                                hx_indicator=f"#{chart_id}-loading",
                                cls="w-full h-48 sm:h-56"
                            ),
                            create_loading_spinner(
                                id=f"{chart_id}-loading",
                                size="w-8 h-8",
                                container_classes="absolute inset-0 flex items-center justify-center pointer-events-none hidden"
                            ),
                            cls="relative w-full"
                        ),
                        ft.Div(
                            ft.A(
                                "Cardmarket",
                                href=cm_url,
                                target="_blank",
                                rel="noopener",
                                cls="flex-1 text-center px-4 py-2 bg-green-700/30 hover:bg-green-600 text-green-300 hover:text-white text-xs font-medium rounded-l-lg transition-colors border-r border-green-900/40",
                            ),
                            ft.A(
                                "TCGPlayer",
                                href=tcg_url,
                                target="_blank",
                                rel="noopener",
                                cls="flex-1 text-center px-4 py-2 bg-blue-700/30 hover:bg-blue-600 text-blue-300 hover:text-white text-xs font-medium rounded-r-lg transition-colors",
                            ),
                            cls="flex w-full mt-3"
                        ),
                        cls="px-5 py-4"
                    ),
                    cls="watchlist-card-item bg-gray-800/60 border border-gray-700 rounded-xl overflow-hidden",
                    data_eur_price=str(item['latest_eur']),
                    data_usd_price=str(item['latest_usd']),
                )
            )

        content = ft.Div(
            *items,
            cls="grid grid-cols-1 gap-6"
        )

        # Add sorting options for grid view
        sort_options = ft.Div(
            ft.Span("Sort by:", cls="text-gray-400 mr-2 text-sm"),
            ft.A(
                ft.Span("Name"),
                ft.I(cls=f"fas fa-sort-{'up' if sort_order == 'asc' else 'down'} ml-1" if sort_by == 'name' else "fas fa-sort ml-1 opacity-50"),
                href=build_url(view="list", sort="name", order="desc" if sort_by == "name" and sort_order == "asc" else "asc"),
                cls=f"mr-4 text-sm font-medium transition-colors flex items-center {'text-blue-400' if sort_by == 'name' else 'text-gray-400 hover:text-white'}"
            ),
            ft.A(
                ft.Span("Price"),
                ft.I(cls=f"fas fa-sort-{'up' if sort_order == 'asc' else 'down'} ml-1" if sort_by == 'price' else "fas fa-sort ml-1 opacity-50"),
                href=build_url(view="list", sort="price", order="desc" if sort_by == "price" and sort_order == "asc" else "asc"),
                cls=f"text-sm font-medium transition-colors flex items-center {'text-blue-400' if sort_by == 'price' else 'text-gray-400 hover:text-white'}"
            ),
            cls="flex items-center mb-4 justify-end"
        )

        # Prepend sort options to content
        content = ft.Div(sort_options, content)

    # Portfolio summary section
    tag_param = f"&tag={tag_filter}" if tag_filter else ""
    collection_label = f'"{tag_filter}"' if tag_filter else "All Cards"

    portfolio_section = ft.Div(
        # Stats row
        ft.Div(
            ft.Div(
                ft.Span("Total EUR", cls="text-xs text-gray-500 uppercase tracking-widest block mb-1"),
                ft.Span(f"€{total_eur:.2f}", cls="text-2xl font-bold text-white font-mono tabular-nums"),
                cls="flex flex-col"
            ),
            ft.Div(cls="w-px bg-gray-700 self-stretch mx-2"),
            ft.Div(
                ft.Span("Total USD", cls="text-xs text-gray-500 uppercase tracking-widest block mb-1"),
                ft.Span(f"${total_usd:.2f}", cls="text-2xl font-bold text-white font-mono tabular-nums"),
                cls="flex flex-col"
            ),
            ft.Div(cls="w-px bg-gray-700 self-stretch mx-2"),
            ft.Div(
                ft.Span("Cards", cls="text-xs text-gray-500 uppercase tracking-widest block mb-1"),
                ft.Span(str(card_count), cls="text-2xl font-bold text-white font-mono tabular-nums"),
                cls="flex flex-col"
            ),
            ft.Div(cls="w-px bg-gray-700 self-stretch mx-2"),
            ft.Div(
                ft.Span("Copies", cls="text-xs text-gray-500 uppercase tracking-widest block mb-1"),
                ft.Span(str(total_copies), cls="text-2xl font-bold text-white font-mono tabular-nums"),
                cls="flex flex-col"
            ),
            ft.Div(
                ft.Span("Collection", cls="text-xs text-gray-500 uppercase tracking-widest block mb-1"),
                ft.Span(collection_label, cls="text-sm font-medium text-blue-400 truncate max-w-[140px]"),
                cls="flex flex-col ml-auto"
            ),
            cls="flex items-center gap-4 sm:gap-6 px-5 py-4 border-b border-gray-700/60"
        ),
        # Chart area
        ft.Div(
            # Time selector
            ft.Div(
                ft.Span("Portfolio Value Over Time", cls="text-xs text-gray-400 uppercase tracking-wider font-medium"),
                ft.Select(
                    ft.Option("30 days", value="30"),
                    ft.Option("90 days", value="90", selected=True),
                    ft.Option("180 days", value="180"),
                    ft.Option("1 year", value="365"),
                    ft.Option("All time", value="1000"),
                    name="days",
                    cls="bg-gray-800 text-white border border-gray-600 rounded px-2 py-0.5 text-xs focus:outline-none focus:border-blue-500 cursor-pointer hover:bg-gray-700 transition-colors",
                    hx_get="/api/watchlist/aggregate-chart",
                    hx_target="#portfolio-aggregate-chart-container",
                    hx_swap="innerHTML",
                    hx_indicator="#portfolio-chart-loading",
                    hx_vals=f'{{"tag": "{tag_filter}"}}',
                    hx_on__before_request="document.getElementById('portfolio-aggregate-chart-container').innerHTML=''; document.getElementById('portfolio-chart-loading').classList.remove('hidden');"
                ),
                cls="flex items-center justify-between mb-3"
            ),
            # Chart container
            ft.Div(
                ft.Div(
                    id="portfolio-aggregate-chart-container",
                    hx_get=f"/api/watchlist/aggregate-chart?days=90{tag_param}",
                    hx_trigger="load",
                    hx_indicator="#portfolio-chart-loading",
                    hx_on__after_request="document.getElementById('portfolio-chart-loading').classList.add('hidden');",
                    cls="w-full h-full"
                ),
                create_loading_spinner(
                    id="portfolio-chart-loading",
                    size="w-6 h-6",
                    container_classes="absolute inset-0 flex items-center justify-center pointer-events-none hidden"
                ),
                cls="relative h-52 sm:h-64 w-full"
            ),
            cls="px-5 py-4"
        ),
        cls="bg-gray-800/60 border border-gray-700 rounded-xl mb-6 overflow-hidden"
    )

    return ft.Div(
        _qty_script(),
        _table_time_range_script() if view_mode == 'table' else ft.Span(),
        ft.Div(
            ft.H1("My Watchlist", cls="text-2xl font-bold text-white"),
            ft.Div(section_switcher, view_switcher, cls="flex flex-wrap items-center gap-3"),
            cls="flex flex-wrap justify-between gap-y-3 items-center mb-6"
        ),
        tag_filter_bar,
        portfolio_section,
        content,
        cls="container mx-auto px-4 py-8"
    )

