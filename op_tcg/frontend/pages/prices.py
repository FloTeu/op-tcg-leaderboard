import json
from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, OPTcgCardRarity
from op_tcg.backend.models.sealed import SealedProductOrderBy
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.frontend.components.layout import create_mobile_filter_button
import time
from datetime import datetime, timedelta

HX_INCLUDE = "[name='currency'],[name='start_date'],[name='end_date'],[name='min_latest_price'],[name='max_latest_price'],[name='order_by'],[name='include_alt_art'],[name='change_metric'],[name='query'],[name='rarity'],[name='price_tab']"

_LABEL_STYLE = "font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.65rem; color:#475569; text-transform:uppercase; display:block; margin-bottom:6px;"


def _styles() -> ft.Style:
    return ft.Style("""
.pr-page { font-family: 'Barlow', sans-serif; }

.meta-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
    padding: 20px;
}
@media (min-width: 768px) { .meta-panel { padding: 24px 28px; } }

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
.meta-select::placeholder { color: #1e2d45; }

.meta-section-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    color: #475569;
    font-size: 0.65rem;
    text-transform: uppercase;
    display: block;
    margin-bottom: 6px;
}

.pr-checkbox-wrapper {
    display: flex;
    align-items: center;
    gap: 10px;
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 8px 12px;
    cursor: pointer;
    transition: border-color 0.15s;
}
.pr-checkbox-wrapper:hover { border-color: #2d3f5a; }
.pr-checkbox-wrapper input[type="checkbox"] {
    width: 15px;
    height: 15px;
    accent-color: #38bdf8;
    cursor: pointer;
    flex-shrink: 0;
}

.price-tab {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    font-size: 0.8rem;
    padding: 6px 16px;
    border-radius: 20px;
    border: 1px solid #1a2540;
    background: #0d1424;
    color: #475569;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, background 0.15s;
}
.price-tab:hover { color: #94a3b8; border-color: #2d3f5a; }
.price-tab-active {
    background: rgba(245,158,11,0.12);
    color: #f59e0b;
    border-color: rgba(245,158,11,0.35);
}
""")


def create_filter_components(selected_currency: CardCurrency = CardCurrency.EURO, start_date: int = None, end_date: int = None):
    now = int(time.time())
    one_year_ago = int((datetime.now() - timedelta(days=365)).timestamp())

    if start_date is None:
        start_date = int((datetime.now() - timedelta(weeks=4)).timestamp())
    if end_date is None:
        end_date = now

    _hx = dict(
        hx_get="/api/price-overview",
        hx_trigger="change",
        hx_target="#price-overview",
        hx_include=HX_INCLUDE,
        hx_indicator="#price-loading-indicator",
    )

    return ft.Div(
        # Include Alt Art
        ft.Div(
            ft.Span("Include Alt Art", style=_LABEL_STYLE),
            ft.Label(
                ft.Input(
                    type="checkbox",
                    name="include_alt_art",
                    checked=False,
                    data_pr_filter="true",
                    **{**_hx, "hx_include": HX_INCLUDE + ",[name='include_alt_art']"},
                ),
                ft.Span("Show alternate art versions",
                        style="font-family:'Barlow',sans-serif; font-size:0.8rem; color:#94a3b8;"),
                cls="pr-checkbox-wrapper",
            ),
            id="filter-section-alt-art",
            cls="mb-4",
        ),
        # Order By
        ft.Div(
            ft.Span("Order By", style=_LABEL_STYLE),
            ft.Select(
                ft.Option("Top Rising", value="rising", selected=True),
                ft.Option("Top Fallers", value="fallers"),
                ft.Option("Most Expensive", value="expensive"),
                ft.Option("Higher in EUR (vs USD)", value="diff_eur_high"),
                ft.Option("Higher in USD (vs EUR)", value="diff_usd_high"),
                id="price-order-by-select",
                name="order_by",
                cls="meta-select styled-select",
                data_pr_filter="true",
                **_hx,
            ),
            cls="mb-4",
        ),
        # Change Metric
        ft.Div(
            ft.Span("Change Metric", style=_LABEL_STYLE),
            ft.Select(
                ft.Option("Absolute", value="absolute", selected=True),
                ft.Option("Relative (%)", value="relative"),
                id="price-change-metric-select",
                name="change_metric",
                cls="meta-select styled-select",
                data_pr_filter="true",
                **{**_hx, "hx_include": HX_INCLUDE + ",[name='change_metric']"},
            ),
            id="filter-section-change-metric",
            cls="mb-4",
        ),
        # Card Rarity
        ft.Div(
            ft.Span("Card Rarity", style=_LABEL_STYLE),
            ft.Select(
                ft.Option("All Rarities", value="All", selected=True),
                *[ft.Option(rarity.value, value=rarity.value) for rarity in OPTcgCardRarity],
                id="price-rarity-select",
                name="rarity",
                cls="meta-select styled-select",
                data_pr_filter="true",
                **_hx,
            ),
            id="filter-section-rarity",
            cls="mb-4",
        ),
        # Currency
        ft.Div(
            ft.Span("Currency", style=_LABEL_STYLE),
            ft.Select(
                ft.Option("EUR (€)", value=CardCurrency.EURO, selected=(selected_currency == CardCurrency.EURO)),
                ft.Option("USD ($)", value=CardCurrency.US_DOLLAR, selected=(selected_currency == CardCurrency.US_DOLLAR)),
                id="price-currency-select",
                name="currency",
                cls="meta-select styled-select",
                data_pr_filter="true",
                **_hx,
            ),
            cls="mb-4",
        ),
        # Date Range
        ft.Div(
            ft.Span("Date Range", style=_LABEL_STYLE),
            ft.Div(
                ft.Div(
                    ft.Div(cls="slider-track"),
                    ft.Input(
                        type="range", min=str(one_year_ago), max=str(now), value=str(start_date),
                        name="start_date", cls="slider-range min-range", data_pr_filter="true", **_hx,
                    ),
                    ft.Input(
                        type="range", min=str(one_year_ago), max=str(now), value=str(end_date),
                        name="end_date", cls="slider-range max-range", data_pr_filter="true", **_hx,
                    ),
                    ft.Div(
                        ft.Span(cls="min-value",
                                style="font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#94a3b8;"),
                        ft.Span(" — ", style="color:#475569; margin:0 4px;"),
                        ft.Span(cls="max-value",
                                style="font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#94a3b8;"),
                        cls="slider-values",
                    ),
                    cls="double-range-slider",
                    id="date-range-slider",
                    data_double_range_slider="true",
                    data_type="date",
                ),
                cls="relative w-full",
            ),
            id="filter-section-date-range",
            cls="mb-4",
        ),
        # Price Range
        ft.Div(
            ft.Span("Price Range", style=_LABEL_STYLE),
            ft.Div(
                ft.Div(
                    ft.Div(cls="slider-track"),
                    ft.Input(
                        type="range", min="0", max="1000", value="0",
                        name="min_latest_price", cls="slider-range min-range", data_pr_filter="true", **_hx,
                    ),
                    ft.Input(
                        type="range", min="0", max="1000", value="1000",
                        name="max_latest_price", cls="slider-range max-range", data_pr_filter="true", **_hx,
                    ),
                    ft.Div(
                        ft.Span("0", cls="min-value",
                                style="font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#94a3b8;"),
                        ft.Span(" — ", style="color:#475569; margin:0 4px;"),
                        ft.Span("1000", cls="max-value",
                                style="font-family:'Share Tech Mono',monospace; font-size:0.75rem; color:#94a3b8;"),
                        cls="slider-values",
                    ),
                    cls="double-range-slider",
                    id="price-range-slider",
                    data_double_range_slider="true",
                ),
                cls="relative w-full",
            ),
            cls="mb-4",
        ),
        cls="space-y-0",
    )


def _tab_switcher() -> ft.Div:
    return ft.Div(
        ft.Button(
            "Cards",
            id="tab-cards",
            cls="price-tab price-tab-active",
            hx_get="/api/price-overview",
            hx_target="#price-overview",
            hx_swap="innerHTML",
            hx_include=HX_INCLUDE,
            hx_vals='{"price_tab":"cards"}',
            hx_indicator="#price-loading-indicator",
        ),
        ft.Button(
            "Sealed Products",
            id="tab-sealed",
            cls="price-tab",
            hx_get="/api/price-overview",
            hx_target="#price-overview",
            hx_swap="innerHTML",
            hx_include=HX_INCLUDE,
            hx_vals='{"price_tab":"sealed"}',
            hx_indicator="#price-loading-indicator",
        ),
        cls="flex gap-2 mb-4",
    )


_CARD_ORDER_OPTIONS = [
    ("rising", "Top Rising"),
    ("fallers", "Top Fallers"),
    ("expensive", "Most Expensive"),
    ("diff_eur_high", "Higher in EUR (vs USD)"),
    ("diff_usd_high", "Higher in USD (vs EUR)"),
]
_SEALED_ORDER_OPTIONS = [(o.value, o.label) for o in SealedProductOrderBy]


def _price_tab_script() -> ft.Script:
    card_opts_json = json.dumps(_CARD_ORDER_OPTIONS)
    sealed_opts_json = json.dumps(_SEALED_ORDER_OPTIONS)
    return ft.Script(f"""
(function() {{
  var CARD_OPTS = {card_opts_json};
  var SEALED_OPTS = {sealed_opts_json};
  var SEALED_ONLY_SECTIONS = ['filter-section-alt-art','filter-section-change-metric','filter-section-rarity','filter-section-date-range'];

  function rebuildOrderBy(opts) {{
    var sel = document.getElementById('price-order-by-select');
    if (!sel) return;
    var cur = sel.value;

    sel.innerHTML = '';
    var matched = false;
    opts.forEach(function(o) {{
      var opt = document.createElement('option');
      opt.value = o[0]; opt.textContent = o[1];
      if (o[0] === cur) {{ opt.selected = true; matched = true; }}
      sel.appendChild(opt);
    }});
    if (!matched && sel.options.length > 0) sel.options[0].selected = true;

    // Also rebuild the custom styled-select wrapper's visible UI
    var container = sel.closest('.multi-select-container');
    if (!container) return;
    var dropdown = container.querySelector('.multi-select-dropdown');
    var display  = container.querySelector('.multi-select');
    if (dropdown) {{
      dropdown.innerHTML = '';
      opts.forEach(function(o) {{
        var div = document.createElement('div');
        div.className = 'dropdown-option';
        div.textContent = o[1];
        div.dataset.value = o[0];
        if (o[0] === sel.value) div.classList.add('selected');
        dropdown.appendChild(div);
      }});
    }}
    if (display) {{
      var selOpt = Array.from(sel.options).find(function(o) {{ return o.selected; }});
      display.textContent = selOpt ? selOpt.text : 'Select an option...';
    }}
  }}

  window.applyPriceTab = function(tab) {{
    var sealed = tab === 'sealed';

    document.querySelectorAll('.price-tab').forEach(function(el) {{ el.classList.remove('price-tab-active'); }});
    var btn = document.getElementById('tab-' + tab);
    if (btn) btn.classList.add('price-tab-active');

    var tabInput = document.getElementById('active-price-tab');
    if (tabInput) tabInput.value = tab;

    var label  = document.getElementById('price-search-label');
    var search = document.getElementById('price-search-input');
    if (label)  label.textContent = sealed ? 'Search Sealed Products' : 'Search Cards';
    if (search) search.setAttribute('placeholder', sealed ? 'Search sealed products...' : 'Search by name, meta format, ID...');

    SEALED_ONLY_SECTIONS.forEach(function(id) {{
      var el = document.getElementById(id);
      if (el) el.style.display = sealed ? 'none' : '';
    }});

    rebuildOrderBy(sealed ? SEALED_OPTS : CARD_OPTS);
  }};

  // Re-apply tab state after every HTMX swap targeting #price-overview
  document.body.addEventListener('htmx:afterSettle', function(evt) {{
    var cfg = evt.detail && evt.detail.requestConfig;
    if (!cfg || (cfg.path || '').indexOf('/api/price-overview') !== 0) return;
    var params = cfg.parameters || {{}};
    var tab = params.price_tab;
    if (Array.isArray(tab)) tab = tab[0];
    if (!tab) {{
      var input = document.getElementById('active-price-tab');
      tab = (input && input.value) || 'cards';
    }}
    window.applyPriceTab(tab);
  }});
}})();
""")


def prices_page():
    return ft.Div(
        _styles(),
        _price_tab_script(),
        ft.Div(
            ft.Div(
                ft.H1("CARD PRICES",
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; line-height:1; margin-bottom:6px;"),
                ft.P(
                    "Track price movements and discover rising cards across the market.",
                    style="font-family:'Barlow',sans-serif; font-size:0.875rem; color:#475569;",
                ),
                cls="mb-6",
                style="padding-bottom:16px; border-bottom:1px solid #111d30;",
            ),
            create_mobile_filter_button(),
            ft.Input(type="hidden", id="active-price-tab", name="price_tab", value="cards"),
            ft.Div(id="prices-header-container"),
            _tab_switcher(),
            ft.Div(
                ft.Span("Search Cards", id="price-search-label", style=_LABEL_STYLE),
                ft.Input(
                    type="search",
                    id="price-search-input",
                    name="query",
                    placeholder="Search by name, meta format, ID…",
                    cls="meta-select",
                    hx_get="/api/price-overview",
                    hx_trigger="keyup changed delay:500ms, search",
                    hx_target="#price-overview",
                    hx_include=HX_INCLUDE,
                    hx_indicator="#price-loading-indicator",
                ),
                cls="mb-4 mt-2",
            ),
            create_loading_spinner(
                id="price-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[100px]",
            ),
            ft.Div(
                hx_get="/api/price-overview",
                hx_trigger="load",
                hx_target="#price-overview",
                hx_swap="innerHTML",
                hx_include=HX_INCLUDE,
                hx_indicator="#price-loading-indicator",
                id="price-overview",
                cls="min-h-screen",
            ),
            cls="pr-page bg-deep-navy px-4 py-4 md:px-6 md:py-6 min-h-screen",
            style="max-width:1280px; margin:0 auto;",
        ),
    )
