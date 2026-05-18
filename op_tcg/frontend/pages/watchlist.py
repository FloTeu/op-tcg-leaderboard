import re
from fasthtml import ft
from op_tcg.backend.db import get_watchlist, get_user_settings, get_decklist_watchlist, get_custom_decklists
from op_tcg.frontend.components.watchlist_toggle import create_watchlist_toggle
from op_tcg.frontend.components.decklist_watchlist_toggle import create_decklist_watchlist_toggle
from op_tcg.frontend.utils.card_price import get_marketplace_link
from op_tcg.frontend.utils.extract import get_card_lookup_by_id_and_aa, get_card_id_card_data_lookup
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.backend.models.cards import CardCurrency


def _wl_styles() -> ft.Style:
    return ft.Style("""
@import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Barlow:wght@300;400;500;600;700&family=Share+Tech+Mono&display=swap');

.wl-page { background: #070b14; font-family: 'Barlow', sans-serif; min-height: 100vh; }
.wl-panel { background: #0d1424; border: 1px solid #1a2540; border-radius: 12px; overflow: hidden; }
.wl-sep { border-top: 1px solid #1a2540; }

.wl-tab {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 5px 14px; border-radius: 20px;
    font-family: 'Bebas Neue', sans-serif; letter-spacing: .08em; font-size: .8rem;
    background: #0d1424; border: 1px solid #1a2540; color: #334155;
    cursor: pointer; text-decoration: none; transition: all .12s; white-space: nowrap;
}
.wl-tab:hover { border-color: #2d3f5a; color: #64748b; }
.wl-tab-active-gold { background: rgba(245,158,11,.12); color: #f59e0b; border-color: rgba(245,158,11,.35); }
.wl-tab-active-cyan { background: rgba(56,189,248,.10); color: #38bdf8; border-color: rgba(56,189,248,.30); }

.wl-badge {
    display: inline-flex; align-items: center;
    padding: 2px 8px; border-radius: 20px; border: 1px solid;
    font-family: 'Share Tech Mono', monospace; font-size: .6rem; white-space: nowrap;
}
.wl-badge-gold { background: rgba(245,158,11,.10); color: #f59e0b; border-color: rgba(245,158,11,.28); }
.wl-badge-cyan { background: rgba(56,189,248,.08); color: #38bdf8; border-color: rgba(56,189,248,.22); }

.wl-tag {
    display: inline-block;
    background: rgba(56,189,248,.07); color: #38bdf8;
    border: 1px solid rgba(56,189,248,.18);
    font-family: 'Barlow', sans-serif; font-size: .62rem; font-weight: 500;
    padding: 1px 7px; border-radius: 10px;
}

/* qty stepper — class names kept for JS compatibility */
.qty-btn {
    width: 28px; height: 28px; display: flex; align-items: center; justify-content: center;
    background: #0d1424; border: 1px solid #1a2540; color: #475569;
    font-size: .85rem; line-height: 1; cursor: pointer; transition: all .12s;
}
.qty-btn:first-child { border-radius: 4px 0 0 4px; }
.qty-btn:last-child { border-radius: 0 4px 4px 0; border-left: none; }
.qty-btn:hover { border-color: #2d3f5a; color: #94a3b8; }
.qty-value {
    width: 32px; height: 28px; display: flex; align-items: center; justify-content: center;
    font-family: 'Share Tech Mono', monospace; font-size: .75rem; color: #f1f5f9;
    background: #080e1c; border-top: 1px solid #1a2540; border-bottom: 1px solid #1a2540;
    user-select: none; text-align: center;
}

.wl-item { background: #0d1424; border: 1px solid #1a2540; border-radius: 12px; overflow: hidden; transition: border-color .18s; }
.wl-item:hover { border-color: #2d3f5a; }

.wl-expand-btn {
    width: 100%; display: flex; align-items: center; justify-content: center; gap: 6px;
    padding: 8px 12px; background: transparent; border: none; border-top: 1px solid #1a2540;
    font-family: 'Barlow', sans-serif; font-size: .68rem; color: #334155;
    cursor: pointer; transition: all .12s;
}
.wl-expand-btn:hover { color: #64748b; background: rgba(245,158,11,.03); }

.wl-stat-label {
    font-family: 'Bebas Neue', sans-serif; letter-spacing: .1em; font-size: .55rem;
    color: #334155; display: block; margin-bottom: 3px;
}
.wl-stat-val { font-family: 'Share Tech Mono', monospace; font-size: 1.5rem; color: #f1f5f9; line-height: 1; }

.wl-btn-primary {
    display: inline-flex; align-items: center; gap: 6px;
    padding: 6px 14px; border-radius: 8px;
    background: #f59e0b; color: #000;
    font-family: 'Bebas Neue', sans-serif; letter-spacing: .08em; font-size: .8rem;
    border: none; cursor: pointer; text-decoration: none; transition: all .12s; white-space: nowrap;
}
.wl-btn-primary:hover { background: #fbbf24; transform: translateY(-1px); }

.wl-btn-ghost {
    display: inline-flex; align-items: center; justify-content: center; gap: 5px;
    padding: 5px 10px; border-radius: 6px;
    background: transparent; color: #475569;
    font-family: 'Barlow', sans-serif; font-size: .72rem; font-weight: 500;
    border: 1px solid #1a2540; cursor: pointer; text-decoration: none; transition: all .12s;
}
.wl-btn-ghost:hover { color: #94a3b8; border-color: #2d3f5a; background: #080e1c; }
.wl-btn-danger:hover { color: #ef4444; border-color: rgba(239,68,68,.35); background: rgba(239,68,68,.07); }

.wl-input {
    background: #080e1c; color: #f1f5f9; border: 1px solid #1a2540;
    border-radius: 6px; padding: 5px 10px;
    font-family: 'Barlow', sans-serif; font-size: .75rem; outline: none; width: 100%;
    transition: border-color .15s;
}
.wl-input:focus { border-color: #38bdf8; }
.wl-input::placeholder { color: #1e2d45; }

.wl-select {
    background: #080e1c; color: #f1f5f9; border: 1px solid #1a2540;
    border-radius: 6px; padding: 3px 8px;
    font-family: 'Barlow', sans-serif; font-size: .7rem; outline: none;
    cursor: pointer; transition: border-color .15s;
}
.wl-select:focus { border-color: #38bdf8; }

.wl-section-label {
    font-family: 'Bebas Neue', sans-serif; letter-spacing: .12em; font-size: .6rem;
    color: #334155; margin-bottom: 10px; display: block;
}

.wl-table { min-width: 100%; }
.wl-th {
    padding: 12px 16px; text-align: left;
    font-family: 'Bebas Neue', sans-serif; letter-spacing: .1em; font-size: .58rem;
    color: #334155; white-space: nowrap; border-bottom: 1px solid #1a2540;
}
.wl-tr { transition: background .1s; }
.wl-tr + .wl-tr { border-top: 1px solid rgba(26,37,64,.5); }
.wl-tr:hover { background: rgba(245,158,11,.02); }
.wl-td { padding: 12px 16px; vertical-align: middle; }

.wl-scroll::-webkit-scrollbar { width: 3px; }
.wl-scroll::-webkit-scrollbar-track { background: transparent; }
.wl-scroll::-webkit-scrollbar-thumb { background: #1a2540; border-radius: 2px; }

.wl-sort-link {
    display: inline-flex; align-items: center; gap: 4px;
    font-family: 'Barlow', sans-serif; font-size: .7rem; font-weight: 500;
    color: #334155; text-decoration: none; transition: color .12s;
}
.wl-sort-link:hover { color: #64748b; }
.wl-sort-active { color: #f59e0b; }

.wl-price-link {
    display: flex; align-items: center; justify-content: flex-end;
    gap: 6px; padding: 4px 8px; border-radius: 5px; text-decoration: none;
    transition: background .12s;
}
.wl-price-eur { color: #10b981; }
.wl-price-eur:hover { background: rgba(16,185,129,.08); }
.wl-price-usd { color: #38bdf8; }
.wl-price-usd:hover { background: rgba(56,189,248,.08); }
.wl-price-badge {
    font-family: 'Barlow', sans-serif; font-size: .6rem; font-weight: 600;
    padding: 1px 5px; border-radius: 3px;
}
.wl-price-eur .wl-price-badge { background: rgba(16,185,129,.15); color: #10b981; }
.wl-price-usd .wl-price-badge { background: rgba(56,189,248,.12); color: #38bdf8; }
""")


def _qty_stepper(card_id: str, aa_version: int, language: str, quantity: int) -> ft.Div:
    """−/count/+ quantity stepper. JS in _qty_script() handles clicks."""
    return ft.Div(
        ft.Button("−", type="button", cls="qty-btn", data_delta="-1"),
        ft.Span(str(quantity), cls="qty-value"),
        ft.Button("+", type="button", cls="qty-btn", data_delta="1"),
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
    dl_watchlist = get_decklist_watchlist(user_id)
    card_lookup = get_card_id_card_data_lookup()

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
        ft.A("ALL", href=build_url(tag=""),
             cls=f"wl-tab {'wl-tab-active-cyan' if not tag_filter else ''}"),
        *[
            ft.A(tag.upper(), href=build_url(tag=tag),
                 cls=f"wl-tab {'wl-tab-active-cyan' if tag_filter == tag else ''}")
            for tag in all_tags
        ],
        cls="flex flex-wrap items-center gap-2 mb-4"
    ) if all_tags else ft.Span()

    if not dl_watchlist and not custom_decklists_all:
        return ft.Div(
            tag_filter_bar,
            ft.Div(
                ft.I(cls="fas fa-layer-group text-4xl mb-3", style="color:#1e2d45;"),
                ft.P("No saved decklists yet.",
                     style="font-family:'Barlow',sans-serif;font-size:.85rem;color:#334155;"),
                ft.P("Open a tournament decklist and click the bookmark icon to save it.",
                     style="font-family:'Barlow',sans-serif;font-size:.75rem;color:#1e2d45;margin-top:4px;"),
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
            *[ft.Span(tag, cls="wl-tag mr-1") for tag in tags],
            ft.Button(
                ft.I(cls="fas fa-pen text-xs"),
                type="button",
                cls="wl-btn-ghost ml-1",
                style="padding:2px 6px;",
                title="Edit tags",
                hx_get=f"/api/watchlist/decklist/tag-editor?leader_id={leader_id}&tournament_id={tournament_id}&player_id={player_id}&tags={tags_str}",
                hx_target=f"#{tag_target_id}",
                hx_swap="outerHTML",
            ),
            id=tag_target_id,
            cls="flex flex-wrap items-center mt-2",
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
                ft.Div(
                    ft.Div(
                        ft.Img(src=image_url, cls="w-14 sm:w-16 h-auto rounded-lg shadow-sm", alt=leader_name)
                        if image_url else ft.Div(cls="w-14 sm:w-16 h-20 rounded-lg",
                                                 style="background:#080e1c;border:1px solid #1a2540;"),
                        cls="flex-shrink-0 mr-4"
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span(leader_id, cls="wl-badge wl-badge-gold"),
                            ft.Span(leader_name,
                                    style="font-family:'Barlow',sans-serif;font-weight:600;font-size:.85rem;color:#f1f5f9;"),
                            *(
                                [ft.Span(meta_format, cls="wl-badge wl-badge-cyan")]
                                if meta_format else []
                            ),
                            cls="flex items-center flex-wrap gap-2 mb-1"
                        ),
                        ft.P(f"Player: {player_id}",
                             style="font-family:'Barlow',sans-serif;font-size:.7rem;color:#475569;"),
                        ft.P(f"Tournament: {tournament_id[:40]}{'...' if len(tournament_id) > 40 else ''}",
                             style="font-family:'Barlow',sans-serif;font-size:.68rem;color:#334155;"),
                        *(
                            [ft.P(f"Played: {tournament_date_str}",
                                  style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#334155;")]
                            if tournament_date_str else []
                        ),
                        tag_chips,
                        cls="flex-1 min-w-0"
                    ),
                    ft.Div(toggle_btn, cls="flex flex-col items-end flex-shrink-0 ml-2"),
                    cls="flex items-start px-4 py-4",
                ),
                ft.Button(
                    ft.I(cls="fas fa-chevron-down text-xs transition-transform",
                         id=f"{expand_btn_id}-icon"),
                    "Show cards",
                    id=expand_btn_id,
                    type="button",
                    cls="wl-expand-btn",
                    onclick=f"toggleDecklistCards('{expand_btn_id}', '{cards_container_id}')",
                ),
                ft.Div(
                    create_loading_spinner(id=f"{cards_container_id}-loading", size="w-5 h-5",
                                          container_classes="flex items-center justify-center py-6 hidden"),
                    id=cards_container_id,
                    cls="hidden",
                    hx_get=cards_url,
                    hx_trigger="expand once",
                    hx_swap="innerHTML",
                    hx_indicator=f"#{cards_container_id}-loading",
                ),
                cls="decklist-watchlist-item wl-item",
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

    # ── Custom decklists subsection ─────────────────────────────────────────
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
            *[ft.Span(tag, cls="wl-tag mr-1") for tag in c_tags],
            ft.Button(
                ft.I(cls="fas fa-pen text-xs"),
                type="button",
                cls="wl-btn-ghost ml-1",
                style="padding:2px 6px;",
                title="Edit tags",
                hx_get=f"/api/watchlist/custom-decklist/tag-editor?custom_id={custom_id}&tags={c_tags_str}",
                hx_target=f"#{c_tag_target_id}",
                hx_swap="outerHTML",
            ),
            id=c_tag_target_id,
            cls="flex flex-wrap items-center mt-2",
            onclick="event.stopPropagation();"
        )

        custom_items.append(
            ft.Div(
                ft.Div(
                    ft.Div(
                        ft.Img(src=c_image_url, cls="w-14 sm:w-16 h-auto rounded-lg shadow-sm", alt=c_leader_name)
                        if c_image_url else ft.Div(cls="w-14 sm:w-16 h-20 rounded-lg",
                                                   style="background:#080e1c;border:1px solid #1a2540;"),
                        cls="flex-shrink-0 mr-4"
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span("CUSTOM", cls="wl-badge wl-badge-gold"),
                            ft.Span(c_name,
                                    style="font-family:'Bebas Neue',sans-serif;letter-spacing:.06em;font-size:1rem;color:#f1f5f9;"),
                            cls="flex items-center flex-wrap gap-2 mb-1"
                        ),
                        ft.P(f"Leader: {c_leader_name}",
                             style="font-family:'Barlow',sans-serif;font-size:.7rem;color:#475569;"),
                        ft.P(f"{c_card_count} cards",
                             style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#334155;"),
                        c_tag_chips,
                        cls="flex-1 min-w-0"
                    ),
                    ft.Div(
                        ft.A(
                            ft.I(cls="fas fa-pen text-xs"),
                            href=f"/deckbuilder?custom_id={custom_id}",
                            cls="wl-btn-ghost",
                            style="width:32px;height:32px;padding:0;",
                            title="Edit decklist",
                        ),
                        ft.Button(
                            ft.I(cls="fas fa-trash text-xs"),
                            type="button",
                            cls="wl-btn-ghost wl-btn-danger mt-1",
                            style="width:32px;height:32px;padding:0;",
                            title="Delete",
                            onclick=f"if(confirm('Delete \"{c_name}\"?')) fetch('/api/watchlist/custom-decklist/delete',{{method:'POST',headers:{{'Content-Type':'application/json'}},body:JSON.stringify({{custom_id:'{custom_id}'}})}})" +
                                    f".then(r=>r.ok && this.closest('.decklist-watchlist-item').remove());",
                        ),
                        cls="flex flex-col items-end flex-shrink-0 ml-2"
                    ),
                    cls="flex items-start px-4 py-4",
                ),
                ft.Button(
                    ft.I(cls="fas fa-chevron-down text-xs transition-transform",
                         id=f"{c_expand_btn_id}-icon"),
                    "Show cards",
                    id=c_expand_btn_id,
                    type="button",
                    cls="wl-expand-btn",
                    onclick=f"toggleDecklistCards('{c_expand_btn_id}', '{c_cards_id}')",
                ),
                ft.Div(
                    create_loading_spinner(id=f"{c_cards_id}-loading", size="w-5 h-5",
                                          container_classes="flex items-center justify-center py-6 hidden"),
                    id=c_cards_id,
                    cls="hidden",
                    hx_get=c_cards_url,
                    hx_trigger="expand once",
                    hx_swap="innerHTML",
                    hx_indicator=f"#{c_cards_id}-loading",
                ),
                cls="decklist-watchlist-item wl-item",
            )
        )

    return ft.Div(
        toggle_script,
        ft.Div(
            tag_filter_bar,
            ft.A(
                ft.I(cls="fas fa-plus text-xs"),
                "NEW DECK",
                href="/deckbuilder",
                cls="wl-btn-primary",
            ),
            cls="flex items-start justify-between gap-3 mb-5"
        ),
        *(
            [ft.Div(
                ft.Span("CUSTOM DECKLISTS", cls="wl-section-label"),
                ft.Div(*custom_items, cls="grid grid-cols-1 gap-3 mb-6"),
            )] if custom_items else []
        ),
        *(
            [ft.Div(
                ft.Span("SAVED DECKLISTS", cls="wl-section-label"),
                ft.Div(*items, cls="grid grid-cols-1 gap-3"),
            )] if items else []
        ),
    )


def watchlist_page(request):
    user = request.session.get('user')
    if not user:
        return ft.Div(
            _wl_styles(),
            ft.Div(
                ft.H1("ACCESS DENIED",
                      style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:.06em;color:#f1f5f9;margin-bottom:8px;"),
                ft.P("Please log in to view your watchlist.",
                     style="font-family:'Barlow',sans-serif;color:#475569;"),
                ft.A("LOG IN", href="/login", cls="wl-btn-primary mt-4 inline-flex"),
                cls="flex flex-col items-center justify-center min-h-screen text-center"
            ),
            cls="wl-page"
        )

    user_id = user.get('sub')
    section = request.query_params.get("section", "cards")

    section_switcher = ft.Div(
        ft.A(
            ft.I(cls="fas fa-clone"),
            "CARDS",
            href="?section=cards",
            cls=f"wl-tab {'wl-tab-active-gold' if section == 'cards' else ''}"
        ),
        ft.A(
            ft.I(cls="fas fa-layer-group"),
            "DECKLISTS",
            href="?section=decklists",
            cls=f"wl-tab {'wl-tab-active-gold' if section == 'decklists' else ''}"
        ),
        cls="flex items-center gap-2"
    )

    if section == 'decklists':
        return ft.Div(
            _wl_styles(),
            ft.Div(
                ft.Div(
                    ft.H1("MY WATCHLIST",
                          style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:.06em;color:#f1f5f9;line-height:1;"),
                    section_switcher,
                    cls="flex flex-wrap justify-between items-center gap-y-3 mb-6"
                ),
                _decklist_watchlist_section(user_id, request),
                cls="container mx-auto px-4 py-8"
            ),
            cls="wl-page"
        )

    watchlist = get_watchlist(user_id)

    if not watchlist:
        return ft.Div(
            _wl_styles(),
            ft.Div(
                ft.Div(
                    ft.H1("MY WATCHLIST",
                          style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:.06em;color:#f1f5f9;line-height:1;"),
                    section_switcher,
                    cls="flex flex-wrap justify-between items-center gap-y-3 mb-6"
                ),
                ft.Div(
                    ft.I(cls="fas fa-heart text-4xl mb-3", style="color:#1e2d45;"),
                    ft.P("Your card watchlist is empty.",
                         style="font-family:'Barlow',sans-serif;font-size:.85rem;color:#334155;"),
                    cls="flex flex-col items-center justify-center py-20 text-center"
                ),
                cls="container mx-auto px-4 py-8"
            ),
            cls="wl-page"
        )

    card_lookup = get_card_lookup_by_id_and_aa()

    view_mode = request.query_params.get("view", "list")
    sort_by = request.query_params.get("sort", "name")
    sort_order = request.query_params.get("order", "asc")
    tag_filter = request.query_params.get("tag", "")

    all_tags = sorted({tag for item in watchlist for tag in item.get('tags', ['my collection'])})

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

    prepared_items = []
    for item in watchlist:
        card_id = item.get('card_id')
        version_val = item.get('card_version', 0)
        try:
            aa_version = int(version_val) if version_val != 'Base' else 0
        except:
            aa_version = 0
        language = item.get('language', 'en')

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
        if latest_eur is None: latest_eur = 0.0
        if latest_usd is None: latest_usd = 0.0

        tags = item.get('tags', ['my collection']) or ['my collection']
        quantity = max(1, int(item.get('quantity', 1)))

        prepared_items.append({
            'card_id': card_id, 'aa_version': aa_version, 'language': language,
            'quantity': quantity, 'card_details': card_details, 'card_name': card_name,
            'image_url': image_url, 'latest_eur': latest_eur, 'latest_usd': latest_usd,
            'tags': tags,
        })

    total_eur = sum(i['latest_eur'] * i['quantity'] for i in prepared_items)
    total_usd = sum(i['latest_usd'] * i['quantity'] for i in prepared_items)
    total_copies = sum(i['quantity'] for i in prepared_items)
    card_count = len(prepared_items)

    reverse = (sort_order == 'desc')
    if sort_by == 'price':
        user_settings = get_user_settings(user_id)
        price_key = 'latest_eur' if user_settings.get('currency') == CardCurrency.EURO else 'latest_usd'
        prepared_items.sort(key=lambda x: x[price_key], reverse=reverse)
    else:
        prepared_items.sort(key=lambda x: x['card_name'], reverse=reverse)

    view_switcher = ft.Div(
        ft.A(
            ft.I(cls="fas fa-th-large"),
            "GRID",
            href=build_url(view="list"),
            cls=f"wl-tab {'wl-tab-active-cyan' if view_mode == 'list' else ''}"
        ),
        ft.A(
            ft.I(cls="fas fa-table"),
            "TABLE",
            href=build_url(view="table"),
            cls=f"wl-tab {'wl-tab-active-cyan' if view_mode == 'table' else ''}"
        ),
        cls="flex items-center gap-2"
    )

    tag_filter_bar = ft.Div(
        ft.A("ALL", href=build_url(tag=""),
             cls=f"wl-tab {'wl-tab-active-cyan' if not tag_filter else ''}"),
        *[
            ft.A(tag.upper(), href=build_url(tag=tag),
                 cls=f"wl-tab {'wl-tab-active-cyan' if tag_filter == tag else ''}")
            for tag in all_tags
        ],
        cls="flex flex-wrap items-center gap-2 mb-5"
    ) if all_tags else ft.Span()

    content = None

    if view_mode == 'table':
        def sort_link(label, column):
            if sort_by == column:
                icon = "fa-sort-up" if sort_order == "asc" else "fa-sort-down"
                new_order = "desc" if sort_order == "asc" else "asc"
                cls = "wl-sort-link wl-sort-active"
            else:
                icon = "fa-sort"
                new_order = "desc" if column == "price" else "asc"
                cls = "wl-sort-link"
            return ft.A(
                ft.Span(label),
                ft.I(cls=f"fas {icon} ml-1 text-xs opacity-60"),
                href=build_url(view="table", sort=column, order=new_order),
                cls=cls
            )

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
                *[ft.Span(tag, cls="wl-tag mr-1") for tag in tags],
                ft.Button(
                    ft.I(cls="fas fa-pen text-xs"),
                    type="button",
                    cls="wl-btn-ghost ml-1",
                    style="padding:2px 6px;",
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
                card_id=card_id, card_version=aa_version, language=language,
                is_in_watchlist=True, include_script=(len(rows) == 0),
                btn_cls="bg-transparent p-2 rounded-full"
            )

            rows.append(
                ft.Tr(
                    ft.Td(
                        ft.Div(
                            ft.Img(src=image_url, cls="w-14 h-auto rounded-lg shadow-sm mr-4 cursor-pointer flex-shrink-0",
                                   style="transition:opacity .15s;",
                                   alt=card_name,
                                   hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                   hx_target="body", hx_swap="beforeend"),
                            ft.Div(
                                ft.Div(card_name,
                                       style="font-family:'Barlow',sans-serif;font-weight:600;font-size:.85rem;color:#f1f5f9;cursor:pointer;",
                                       hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                       hx_target="body", hx_swap="beforeend"),
                                ft.Div(card_id,
                                       style="font-family:'Share Tech Mono',monospace;font-size:.65rem;color:#334155;margin-top:2px;"),
                                tag_chips,
                                cls="flex flex-col min-w-0"
                            ),
                            cls="flex items-center"
                        ),
                        cls="wl-td align-top"
                    ),
                    ft.Td(
                        ft.Div(
                            ft.A(
                                ft.Span(f"€{item['latest_eur'] * quantity:.2f}",
                                        style="font-family:'Share Tech Mono',monospace;font-size:.8rem;color:#10b981;",
                                        data_price_eur=True),
                                ft.Span("CM", cls="wl-price-badge",
                                        style="background:rgba(16,185,129,.12);color:#10b981;font-family:'Barlow';font-size:.58rem;font-weight:600;padding:1px 5px;border-radius:3px;"),
                                href=cm_url, target="_blank",
                                cls="flex items-center justify-end gap-2 py-1 px-2 rounded hover:bg-green-900/10 transition-colors mb-1"
                            ),
                            ft.A(
                                ft.Span(f"${item['latest_usd'] * quantity:.2f}",
                                        style="font-family:'Share Tech Mono',monospace;font-size:.8rem;color:#38bdf8;",
                                        data_price_usd=True),
                                ft.Span("TCG", cls="wl-price-badge",
                                        style="background:rgba(56,189,248,.10);color:#38bdf8;font-family:'Barlow';font-size:.58rem;font-weight:600;padding:1px 5px;border-radius:3px;"),
                                href=tcg_url, target="_blank",
                                cls="flex items-center justify-end gap-2 py-1 px-2 rounded hover:bg-blue-900/10 transition-colors"
                            ),
                            cls="flex flex-col items-end min-w-[110px]"
                        ),
                        cls="wl-td whitespace-nowrap"
                    ),
                    ft.Td(
                        ft.Div(
                            ft.Div(version_label,
                                   style="font-family:'Barlow',sans-serif;font-size:.75rem;color:#94a3b8;"),
                            ft.Div(language.upper(),
                                   style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#334155;margin-top:2px;"),
                            cls="flex flex-col"
                        ),
                        cls="wl-td whitespace-nowrap"
                    ),
                    ft.Td(_qty_stepper(card_id, aa_version, language, quantity), cls="wl-td whitespace-nowrap"),
                    ft.Td(
                        ft.Div(toggle_btn, cls="flex items-center justify-center"),
                        cls="wl-td whitespace-nowrap"
                    ),
                    ft.Td(
                        ft.Div(
                            ft.Div(
                                id=chart_id,
                                hx_get=f"/api/card-price-development-chart?card_id={card_id}&days=90&aa_version={aa_version}&compact=true&location=watchlist",
                                hx_trigger="revealed",
                                hx_indicator=f"#{chart_id}-loading",
                                cls="w-full h-36 table-chart-container",
                                data_card_id=card_id, data_aa_version=str(aa_version),
                            ),
                            create_loading_spinner(
                                id=f"{chart_id}-loading", size="w-6 h-6",
                                container_classes="absolute inset-0 flex items-center justify-center pointer-events-none hidden"
                            ),
                            cls="w-full min-w-[200px] h-36 relative overflow-hidden"
                        ),
                        cls="wl-td w-full"
                    ),
                    cls="wl-tr watchlist-card-item",
                    data_eur_price=str(item['latest_eur']),
                    data_usd_price=str(item['latest_usd']),
                )
            )

        content = ft.Div(
            ft.Table(
                ft.Thead(
                    ft.Tr(
                        ft.Th(sort_link("CARD", "name"), cls="wl-th w-1/3 min-w-[250px]"),
                        ft.Th(sort_link("PRICE", "price"), cls="wl-th w-28"),
                        ft.Th("VERSION", cls="wl-th w-24"),
                        ft.Th("QTY", cls="wl-th w-24"),
                        ft.Th("", cls="wl-th w-16"),
                        ft.Th(
                            ft.Div(
                                ft.Span("PRICE TREND",
                                        style="font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:.58rem;color:#334155;"),
                                ft.Select(
                                    ft.Option("30d", value="30"),
                                    ft.Option("90d", value="90", selected=True),
                                    ft.Option("180d", value="180"),
                                    ft.Option("1y", value="365"),
                                    ft.Option("All", value="1000"),
                                    id="table-global-time-range",
                                    cls="wl-select",
                                    onchange="updateAllTableCharts(this.value)"
                                ),
                                cls="flex items-center gap-3"
                            ),
                            cls="wl-th min-w-[300px]"
                        ),
                    ),
                    cls="wl-thead"
                ),
                ft.Tbody(*rows),
                cls="wl-table"
            ),
            cls="wl-panel overflow-x-auto wl-scroll"
        )

    else:
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

            if card_details:
                cm_url, _ = get_marketplace_link(card_details, CardCurrency.EURO)
                tcg_url, _ = get_marketplace_link(card_details, CardCurrency.US_DOLLAR)
            else:
                cm_url = f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={card_id}"
                tcg_url = f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={card_id}"

            version_label = "Base" if aa_version == 0 else f"Alt Art {aa_version}"
            chart_id = f"chart-{card_id}-{aa_version}-{language}"
            tags_str = ",".join(tags)
            tag_target_id = f"tags-{card_id}-{aa_version}-{language}"

            tag_chips = ft.Div(
                *[ft.Span(tag, cls="wl-tag mr-1") for tag in tags],
                ft.Button(
                    ft.I(cls="fas fa-pen text-xs"),
                    type="button",
                    cls="wl-btn-ghost ml-1",
                    style="padding:2px 6px;",
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
                card_id=card_id, card_version=aa_version, language=language,
                is_in_watchlist=True, include_script=(len(items) == 0)
            )

            items.append(
                ft.Div(
                    ft.Div(
                        ft.Div(
                            ft.Img(src=image_url, cls="w-16 sm:w-20 h-auto rounded-lg shadow-sm",
                                   style="transition:opacity .15s;", alt=card_name),
                            cls="flex-shrink-0 mr-4 cursor-pointer",
                            hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                            hx_target="body", hx_swap="beforeend"
                        ),
                        ft.Div(
                            ft.H3(card_name,
                                  style="font-family:'Barlow',sans-serif;font-weight:600;font-size:.9rem;color:#f1f5f9;line-height:1.3;cursor:pointer;",
                                  hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                  hx_target="body", hx_swap="beforeend"),
                            ft.P(f"{card_id} · {version_label} · {language.upper()}",
                                 style="font-family:'Share Tech Mono',monospace;font-size:.6rem;color:#334155;margin-top:3px;"),
                            ft.Div(
                                ft.Span(f"€{item['latest_eur'] * quantity:.2f}",
                                        style="font-family:'Share Tech Mono',monospace;font-size:.85rem;color:#10b981;font-weight:600;margin-right:10px;",
                                        data_price_eur=True),
                                ft.Span(f"${item['latest_usd'] * quantity:.2f}",
                                        style="font-family:'Share Tech Mono',monospace;font-size:.85rem;color:#334155;",
                                        data_price_usd=True),
                                cls="mt-2"
                            ),
                            tag_chips,
                            cls="flex-1 min-w-0",
                            hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                            hx_target="body", hx_swap="beforeend"
                        ),
                        ft.Div(toggle_btn, cls="flex-shrink-0 ml-2"),
                        cls="flex items-start px-4 py-4",
                        style="border-bottom:1px solid #1a2540;"
                    ),
                    ft.Div(
                        ft.Span("QTY",
                                style="font-family:'Bebas Neue',sans-serif;letter-spacing:.08em;font-size:.65rem;color:#334155;margin-right:10px;"),
                        _qty_stepper(card_id, aa_version, language, quantity),
                        cls="flex items-center px-4 py-2",
                        style="border-bottom:1px solid #1a2540;"
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span("PRICE TREND",
                                    style="font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:.6rem;color:#334155;"),
                            ft.Select(
                                ft.Option("30 Days", value="30"),
                                ft.Option("90 Days", value="90", selected=True),
                                ft.Option("180 Days", value="180"),
                                ft.Option("1 Year", value="365"),
                                ft.Option("All Time", value="1000"),
                                name="days",
                                id=f"price-period-selector-{chart_id}",
                                cls="wl-select",
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
                                id=f"{chart_id}-loading", size="w-8 h-8",
                                container_classes="absolute inset-0 flex items-center justify-center pointer-events-none hidden"
                            ),
                            cls="relative w-full"
                        ),
                        ft.Div(
                            ft.A("Cardmarket", href=cm_url, target="_blank", rel="noopener",
                                 style="flex:1;text-align:center;padding:8px 16px;background:rgba(16,185,129,.08);color:#10b981;font-family:'Barlow',sans-serif;font-size:.72rem;font-weight:500;border-radius:6px 0 0 6px;text-decoration:none;transition:background .12s;",
                                 onmouseover="this.style.background='rgba(16,185,129,.18)'",
                                 onmouseout="this.style.background='rgba(16,185,129,.08)'"),
                            ft.A("TCGPlayer", href=tcg_url, target="_blank", rel="noopener",
                                 style="flex:1;text-align:center;padding:8px 16px;background:rgba(56,189,248,.07);color:#38bdf8;font-family:'Barlow',sans-serif;font-size:.72rem;font-weight:500;border-radius:0 6px 6px 0;text-decoration:none;transition:background .12s;border-left:1px solid #1a2540;",
                                 onmouseover="this.style.background='rgba(56,189,248,.16)'",
                                 onmouseout="this.style.background='rgba(56,189,248,.07)'"),
                            cls="flex w-full mt-3"
                        ),
                        cls="px-4 py-4"
                    ),
                    cls="watchlist-card-item wl-item",
                    data_eur_price=str(item['latest_eur']),
                    data_usd_price=str(item['latest_usd']),
                )
            )

        sort_options = ft.Div(
            ft.Span("SORT BY",
                    style="font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:.6rem;color:#334155;margin-right:10px;"),
            ft.A(
                ft.Span("Name"),
                ft.I(cls=f"fas fa-sort-{'up' if sort_order == 'asc' else 'down'} ml-1 text-xs"
                         if sort_by == 'name' else "fas fa-sort ml-1 text-xs opacity-40"),
                href=build_url(view="list", sort="name", order="desc" if sort_by == "name" and sort_order == "asc" else "asc"),
                cls=f"wl-sort-link mr-4 {'wl-sort-active' if sort_by == 'name' else ''}"
            ),
            ft.A(
                ft.Span("Price"),
                ft.I(cls=f"fas fa-sort-{'up' if sort_order == 'asc' else 'down'} ml-1 text-xs"
                         if sort_by == 'price' else "fas fa-sort ml-1 text-xs opacity-40"),
                href=build_url(view="list", sort="price", order="asc" if sort_by == "price" and sort_order == "desc" else "desc"),
                cls=f"wl-sort-link {'wl-sort-active' if sort_by == 'price' else ''}"
            ),
            cls="flex items-center mb-4 justify-end"
        )

        content = ft.Div(
            sort_options,
            ft.Div(*items, cls="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4")
        )

    # ── Portfolio summary ────────────────────────────────────────────────────
    tag_param = f"&tag={tag_filter}" if tag_filter else ""
    collection_label = f'"{tag_filter}"' if tag_filter else "All Cards"

    def _stat_divider():
        return ft.Div(style="width:1px;background:#1a2540;align-self:stretch;margin:0 4px;flex-shrink:0;")

    portfolio_section = ft.Div(
        ft.Div(
            ft.Div(
                ft.Span("TOTAL EUR", cls="wl-stat-label"),
                ft.Span(f"€{total_eur:.2f}", cls="wl-stat-val"),
                cls="flex flex-col"
            ),
            _stat_divider(),
            ft.Div(
                ft.Span("TOTAL USD", cls="wl-stat-label"),
                ft.Span(f"${total_usd:.2f}", cls="wl-stat-val"),
                cls="flex flex-col"
            ),
            _stat_divider(),
            ft.Div(
                ft.Span("CARDS", cls="wl-stat-label"),
                ft.Span(str(card_count), cls="wl-stat-val"),
                cls="flex flex-col"
            ),
            _stat_divider(),
            ft.Div(
                ft.Span("COPIES", cls="wl-stat-label"),
                ft.Span(str(total_copies), cls="wl-stat-val"),
                cls="flex flex-col"
            ),
            ft.Div(
                ft.Span("COLLECTION", cls="wl-stat-label"),
                ft.Span(collection_label,
                        style="font-family:'Share Tech Mono',monospace;font-size:.75rem;color:#38bdf8;"),
                cls="flex flex-col ml-auto"
            ),
            cls="flex items-center gap-3 sm:gap-5 px-5 py-4",
            style="border-bottom:1px solid #1a2540;"
        ),
        ft.Div(
            ft.Div(
                ft.Span("PORTFOLIO VALUE",
                        style="font-family:'Bebas Neue',sans-serif;letter-spacing:.1em;font-size:.6rem;color:#334155;"),
                ft.Select(
                    ft.Option("30 days", value="30"),
                    ft.Option("90 days", value="90", selected=True),
                    ft.Option("180 days", value="180"),
                    ft.Option("1 year", value="365"),
                    ft.Option("All time", value="1000"),
                    name="days",
                    cls="wl-select",
                    hx_get="/api/watchlist/aggregate-chart",
                    hx_target="#portfolio-aggregate-chart-container",
                    hx_swap="innerHTML",
                    hx_indicator="#portfolio-chart-loading",
                    hx_vals=f'{{"tag": "{tag_filter}"}}',
                    hx_on__before_request="document.getElementById('portfolio-aggregate-chart-container').innerHTML=''; document.getElementById('portfolio-chart-loading').classList.remove('hidden');"
                ),
                cls="flex items-center justify-between mb-3"
            ),
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
                    id="portfolio-chart-loading", size="w-6 h-6",
                    container_classes="absolute inset-0 flex items-center justify-center pointer-events-none hidden"
                ),
                cls="relative h-52 sm:h-64 w-full"
            ),
            cls="px-5 py-4"
        ),
        cls="wl-panel mb-6"
    )

    return ft.Div(
        _wl_styles(),
        _qty_script(),
        _table_time_range_script() if view_mode == 'table' else ft.Span(),
        ft.Div(
            ft.Div(
                ft.H1("MY WATCHLIST",
                      style="font-family:'Bebas Neue',sans-serif;font-size:2rem;letter-spacing:.06em;color:#f1f5f9;line-height:1;"),
                ft.Div(section_switcher, view_switcher, cls="flex flex-wrap items-center gap-2"),
                cls="flex flex-wrap justify-between gap-y-3 items-center mb-6"
            ),
            tag_filter_bar,
            portfolio_section,
            content,
            cls="container mx-auto px-4 py-8"
        ),
        cls="wl-page"
    )
