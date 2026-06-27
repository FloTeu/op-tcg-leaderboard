from collections import defaultdict

from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, ExtendedCardData
from typing import List, Dict
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.sealed import SealedProductType
from op_tcg.frontend.utils.card_price import get_marketplace_link

_SEALED_TYPE_CONFIG = {
    SealedProductType.BOOSTER_BOX: {'label': 'Booster Box', 'color': '#f59e0b', 'bg': 'rgba(245,158,11,0.12)', 'border': 'rgba(245,158,11,0.35)'},
    SealedProductType.BOOSTER_CASE: {'label': 'Booster Case', 'color': '#a855f7', 'bg': 'rgba(168,85,247,0.12)', 'border': 'rgba(168,85,247,0.35)'},
    SealedProductType.PRECONSTRUCTED_DECK: {'label': 'Starter Deck', 'color': '#38bdf8', 'bg': 'rgba(56,189,248,0.10)', 'border': 'rgba(56,189,248,0.30)'},
    SealedProductType.PROMO: {'label': 'Sealed', 'color': '#475569', 'bg': 'rgba(71,85,105,0.12)', 'border': 'rgba(71,85,105,0.35)'},
}
_SEALED_TYPE_ORDER = [SealedProductType.BOOSTER_BOX, SealedProductType.BOOSTER_CASE, SealedProductType.PRECONSTRUCTED_DECK, SealedProductType.PROMO]

def price_tile(item: dict, currency: CardCurrency, card_id2card_data: Dict[str, Dict[int, ExtendedCardData]] | None = None) -> ft.Div:
    symbol = "€" if currency == CardCurrency.EURO else "$"
    name = item.get('name') or item.get('card_id')
    latest = item.get('latest_price') or 0
    pct_change = item.get('pct_change')
    abs_change = item.get('abs_change')
    is_up = (pct_change or 0) > 0
    is_down = (pct_change or 0) < 0
    arrow = "▲" if is_up else ("▼" if is_down else "→")
    pct_str = f"{pct_change * 100:.1f}%" if pct_change is not None else "—"
    abs_str = f"{symbol}{abs_change:.2f}" if abs_change is not None else "—"
    card_id = item.get('card_id')
    aa_version = item.get('aa_version', 0)

    change_color = "#10b981" if is_up else ("#ef4444" if is_down else "#475569")
    change_bg = "rgba(16,185,129,0.1)" if is_up else ("rgba(239,68,68,0.1)" if is_down else "rgba(71,85,105,0.1)")

    latest_meta = MetaFormat.latest_meta_format()
    local_indicator_id = f"price-modal-indicator-{card_id}-{aa_version}"

    image = ft.Img(
        src=item.get('image_url'), alt=name,
        cls="w-full h-auto cursor-pointer",
        style="border-radius:6px 6px 0 0; display:block; transition:opacity 0.15s;",
        hx_get=f"/api/card-modal?card_id={card_id}&meta_format={latest_meta}&aa_version={aa_version}",
        hx_include="[name='currency']",
        hx_target="body", hx_swap="beforeend",
        hx_indicator=f"#{local_indicator_id}",
        onmouseover="this.style.opacity='0.85'",
        onmouseout="this.style.opacity='1'",
    )

    external_link = ft.Span()
    if card_id2card_data and card_id in card_id2card_data:
        card_versions = card_id2card_data[card_id]
        card_data = card_versions.get(aa_version) or card_versions.get(0)
        if card_data:
            marketplace_url, marketplace_text = get_marketplace_link(card_data, currency)
            link_color = "#10b981" if "Cardmarket" in marketplace_text else "#38bdf8"
            external_link = ft.A(
                marketplace_text,
                href=marketplace_url,
                target="_blank",
                rel="noopener",
                style=f"font-family:'Barlow',sans-serif; font-size:0.7rem; color:{link_color}; text-decoration:none; opacity:0.8; transition:opacity 0.12s;",
                onmouseover="this.style.opacity='1'",
                onmouseout="this.style.opacity='0.8'",
            )

    return ft.Div(
        ft.Div(
            image,
            ft.Div(id=local_indicator_id, cls="htmx-indicator", style="display:none;"),
        ),
        ft.Div(
            ft.P(name,
                 style="font-family:'Barlow',sans-serif; font-size:0.8rem; font-weight:600; color:#f1f5f9; white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:5px;"),
            ft.Div(
                ft.Span(f"{symbol}{latest:.2f}",
                        style="font-family:'Share Tech Mono',monospace; font-size:0.95rem; color:#f59e0b; font-weight:700;"),
                ft.Span(
                    f"{arrow} {abs_str} ({pct_str})",
                    style=f"font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:{change_color}; background:{change_bg}; padding:2px 5px; border-radius:4px; white-space:nowrap;",
                ),
                cls="flex items-center justify-between gap-1 mb-2",
            ),
            ft.Div(external_link, cls="flex justify-end"),
            cls="p-2",
        ),
        style="background:#0d1424; border:1px solid #1a2540; border-radius:8px; overflow:hidden; transition:border-color 0.15s, transform 0.15s;",
        onmouseover="this.style.borderColor='#2d3f5a'; this.style.transform='translateY(-2px)';",
        onmouseout="this.style.borderColor='#1a2540'; this.style.transform='translateY(0)';",
    )


def price_tiles(items: List[dict], currency: CardCurrency, card_id2card_data: Dict[str, Dict[int, ExtendedCardData]] | None = None) -> ft.Div:
    return ft.Div(
        ft.Div(
            *[price_tile(it, currency, card_id2card_data) for it in items],
            cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3",
        )
    )


def create_sealed_product_modal(item: dict, currency: CardCurrency) -> ft.Div:
    """Full-screen modal for a sealed product with price chart."""
    symbol = "€" if currency == CardCurrency.EURO else "$"
    name = item.get('name', '')
    product_type = SealedProductType(item.get('product_type', SealedProductType.PROMO))
    from_price = item.get('from_price')
    trend_price = item.get('trend_price')
    image_url = item.get('gcs_image_url') or item.get('image_url')
    url = item.get('url', '#')
    language = str(item.get('language', 'en')).upper()
    release_date = item.get('release_date')
    marketplace = item.get('marketplace', 'cardmarket')
    product_id = item.get('id', '')

    cfg = _SEALED_TYPE_CONFIG.get(product_type, _SEALED_TYPE_CONFIG[SealedProductType.PROMO])
    from_str = f"{symbol}{from_price:.2f}" if from_price is not None else "—"
    trend_str = f"{symbol}{trend_price:.2f}" if trend_price is not None else "—"
    release_str = str(release_date) if release_date else "—"
    currency_val = currency.value

    modal_id = f"sealed-modal-{product_id}"

    _label = "font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:0.65rem; color:#475569; text-transform:uppercase;"
    _value = "font-family:'Share Tech Mono',monospace; font-size:0.8rem; color:#f1f5f9;"
    _row = "display:flex; justify-content:space-between; align-items:center; padding:8px 0; border-bottom:1px solid #1a2540;"

    def info_row(label, value):
        return ft.Div(ft.Span(label, style=_label), ft.Span(value, style=_value), style=_row)

    chart_container_id = f"sealed-price-chart-container-{product_id}"
    chart_loading_id = f"sealed-price-chart-loading-{product_id}"

    return ft.Div(
        ft.Div(
            # Close button
            ft.Button(
                "✕",
                type="button",
                style="position:absolute; top:12px; right:16px; background:none; border:none; color:#475569; font-size:1.2rem; cursor:pointer; z-index:1; transition:color 0.12s;",
                onmouseover="this.style.color='#f1f5f9'",
                onmouseout="this.style.color='#475569'",
                onclick=f"document.getElementById('{modal_id}').remove();",
            ),

            # Content layout: image left, details right
            ft.Div(
                # Image column
                ft.Div(
                    ft.Img(
                        src=image_url,
                        alt=name,
                        style="width:100%; height:auto; object-fit:contain; border-radius:8px; display:block;",
                    ) if image_url else ft.Div(
                        ft.Span("📦", style="font-size:3rem; opacity:0.2;"),
                        style="display:flex; align-items:center; justify-content:center; background:#080e1c; border-radius:8px; min-height:200px;",
                    ),
                    cls="w-full md:w-2/5 flex-shrink-0",
                ),

                # Details column
                ft.Div(
                    # Name + type badge
                    ft.Div(
                        ft.Span(
                            cfg['label'],
                            style=f"font-family:'Bebas Neue',sans-serif; font-size:0.6rem; letter-spacing:0.12em; color:{cfg['color']}; background:{cfg['bg']}; border:1px solid {cfg['border']}; border-radius:4px; padding:2px 6px; display:inline-block; margin-bottom:8px;",
                        ),
                        ft.Div(
                            ft.Span(name, style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.08em; font-size:1.4rem; color:#f1f5f9; line-height:1.15;"),
                            style="",
                        ),
                        style="padding-bottom:12px; border-bottom:1px solid #1a2540; margin-bottom:4px;",
                    ),

                    # Info rows
                    info_row("Language", language),
                    info_row("Marketplace", marketplace.capitalize()),
                    info_row("Released", release_str),

                    # Prices
                    ft.Div(
                        ft.Span("FROM", style=_label),
                        ft.Span(from_str, style="font-family:'Share Tech Mono',monospace; font-size:1rem; color:#10b981; font-weight:700;"),
                        style=_row,
                    ),
                    ft.Div(
                        ft.Span("TREND (30d)", style=_label),
                        ft.Span(trend_str, style="font-family:'Share Tech Mono',monospace; font-size:1rem; color:#f59e0b; font-weight:700;"),
                        style=_row,
                    ),

                    # Marketplace link
                    ft.Div(
                        ft.A(
                            f"View on {marketplace.capitalize()} →",
                            href=url, target="_blank", rel="noopener",
                            style="font-family:'Barlow',sans-serif; font-size:0.8rem; color:#38bdf8; text-decoration:none; transition:opacity 0.12s;",
                            onmouseover="this.style.opacity='0.75'",
                            onmouseout="this.style.opacity='1'",
                        ),
                        style="padding-top:12px;",
                    ),

                    cls="flex-1 min-w-0",
                ),

                cls="flex flex-col md:flex-row gap-6 mb-6",
            ),

            # Price development section
            ft.Div(
                ft.Div(
                    ft.Span("Price Development",
                            style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:1rem; color:#f1f5f9;"),
                    ft.Div(
                        *[
                            ft.Button(
                                label,
                                type="button",
                                cls="sealed-period-chip",
                                style=(
                                    "font-family:'Barlow',sans-serif; font-size:0.75rem; padding:3px 10px;"
                                    "border:1px solid; border-radius:20px; cursor:pointer;"
                                    "transition:background .15s,color .15s,border-color .15s;"
                                    + ("background:rgba(245,158,11,0.12);color:#f59e0b;border-color:rgba(245,158,11,0.35);"
                                       if days_val == "90" else
                                       "background:#0d1424;color:#475569;border-color:#1a2540;")
                                ),
                                hx_get="/api/sealed-product-price-chart",
                                hx_target=f"#{chart_container_id}",
                                hx_indicator=f"#{chart_loading_id}",
                                hx_vals=f'{{"product_id":"{product_id}","currency":"{currency_val}","days":"{days_val}"}}',
                                **{"hx-on::before-request": f"document.getElementById('{chart_container_id}').innerHTML='';"},
                                onclick=(
                                    f"this.closest('.sealed-period-chips').querySelectorAll('.sealed-period-chip')"
                                    ".forEach(function(b){b.style.background='#0d1424';b.style.color='#475569';b.style.borderColor='#1a2540';});"
                                    "this.style.background='rgba(245,158,11,0.12)';this.style.color='#f59e0b';this.style.borderColor='rgba(245,158,11,0.35)';"
                                ),
                            )
                            for label, days_val in [("30d", "30"), ("60d", "60"), ("90d", "90"), ("180d", "180"), ("1yr", "365")]
                        ],
                        cls="flex gap-1.5 flex-wrap sealed-period-chips",
                    ),
                    cls="flex justify-between items-center gap-4 mb-4 flex-wrap",
                ),
                ft.Div(
                    ft.Div(
                        id=chart_container_id,
                        hx_get=f"/api/sealed-product-price-chart?product_id={product_id}&currency={currency_val}&days=90",
                        hx_trigger="load",
                        hx_indicator=f"#{chart_loading_id}",
                        cls="w-full h-full",
                    ),
                    ft.Div(
                        ft.Div(style="width:28px; height:28px; border:2px solid #1a2540; border-top-color:#38bdf8; border-radius:50%; animation:rotate 0.65s linear infinite;"),
                        id=chart_loading_id,
                        cls="htmx-indicator absolute inset-0 flex items-center justify-center",
                        style="opacity:0;",
                    ),
                    cls="relative h-52",
                ),
                style="padding-top:20px; border-top:1px solid #1a2540;",
            ),

            style="background:#0d1424; border:1px solid #1a2540; border-radius:12px; padding:24px; max-width:52rem; width:100%; margin:0 1rem; position:relative;",
            onclick="event.stopPropagation();",
        ),
        ft.Style("@keyframes rotate { to { transform: rotate(360deg); } }"),
        id=modal_id,
        cls="fixed inset-0 flex items-center justify-center overflow-y-auto py-4",
        style="z-index:10000; background:rgba(0,0,0,0.8);",
        onclick=f"document.getElementById('{modal_id}').remove();",
    )


def sealed_product_tile(item: dict, symbol: str, currency: CardCurrency = CardCurrency.EURO) -> ft.Div:
    name = item.get('name', '')
    product_type = SealedProductType(item.get('product_type', SealedProductType.PROMO))
    from_price = item.get('from_price')
    trend_price = item.get('trend_price')
    image_url = item.get('gcs_image_url')
    url = item.get('url', '#')
    language = str(item.get('language', 'en')).upper()[:2]
    product_id = item.get('id', '')
    currency_val = currency.value

    cfg = _SEALED_TYPE_CONFIG.get(product_type)
    from_str = f"{symbol}{from_price:.2f}" if from_price is not None else "—"
    trend_str = f"{symbol}{trend_price:.2f}" if trend_price is not None else "—"

    img_child = ft.Img(
        src=image_url, alt=name,
        style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:contain; display:block; padding:4px;",
    ) if image_url else ft.Div(
        ft.Span("📦", style="font-size:2.5rem; opacity:0.2;"),
        style="position:absolute; top:0; left:0; width:100%; height:100%; display:flex; align-items:center; justify-content:center; background:#080e1c;",
    )

    return ft.Div(
        ft.Div(
            img_child,
            ft.Span(
                language,
                style="position:absolute; top:6px; right:6px; font-family:'Bebas Neue',sans-serif; font-size:0.6rem; letter-spacing:0.1em; color:#94a3b8; background:rgba(7,11,20,0.75); border:1px solid #1a2540; border-radius:3px; padding:1px 5px; z-index:1;",
            ),
            style="position:relative; padding-top:65%; overflow:hidden; background:#080e1c;",
        ),
        ft.Div(
            ft.Span(
                cfg['label'],
                style=f"font-family:'Bebas Neue',sans-serif; font-size:0.6rem; letter-spacing:0.12em; color:{cfg['color']}; background:{cfg['bg']}; border:1px solid {cfg['border']}; border-radius:4px; padding:2px 6px; display:inline-block; margin-bottom:6px;",
            ),
            ft.P(
                name,
                title=name,
                style="font-family:'Barlow',sans-serif; font-size:0.8rem; font-weight:600; color:#f1f5f9; margin-bottom:8px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;",
            ),
            ft.Div(
                ft.Div(
                    ft.Span("FROM", style="font-family:'Bebas Neue',sans-serif; font-size:0.55rem; letter-spacing:0.1em; color:#475569; display:block; margin-bottom:1px;"),
                    ft.Span(from_str, style="font-family:'Share Tech Mono',monospace; font-size:0.9rem; color:#10b981; font-weight:700;"),
                ),
                ft.Div(
                    ft.Span("TREND", style="font-family:'Bebas Neue',sans-serif; font-size:0.55rem; letter-spacing:0.1em; color:#475569; display:block; margin-bottom:1px;"),
                    ft.Span(trend_str, style="font-family:'Share Tech Mono',monospace; font-size:0.9rem; color:#f59e0b; font-weight:700;"),
                ),
                cls="flex justify-between mb-3",
            ),
            ft.Span(
                "View details →",
                style="font-family:'Barlow',sans-serif; font-size:0.7rem; color:#38bdf8; opacity:0.75; cursor:pointer;",
            ),
            cls="p-2",
        ),
        hx_get=f"/api/sealed-product-modal?product_id={product_id}&currency={currency_val}",
        hx_target="body",
        hx_swap="beforeend",
        style="background:#0d1424; border:1px solid #1a2540; border-radius:8px; overflow:hidden; transition:border-color 0.15s, transform 0.15s; cursor:pointer;",
        onmouseover="this.style.borderColor='#2d3f5a'; this.style.transform='translateY(-2px)';",
        onmouseout="this.style.borderColor='#1a2540'; this.style.transform='translateY(0)';",
    )


def sealed_product_tiles(items: List[dict], currency: CardCurrency) -> ft.Div:
    symbol = "€" if currency == CardCurrency.EURO else "$"
    grouped: dict[str, list] = defaultdict(list)
    for item in items:
        grouped[item.get('product_type', 'sealed')].append(item)

    if not items:
        return ft.Div(
            ft.P("No sealed products found.", style="font-family:'Barlow',sans-serif; color:#475569; text-align:center; padding:40px 0;"),
        )

    sections = []
    for pt in _SEALED_TYPE_ORDER:
        group = grouped.get(pt, [])
        if not group:
            continue
        label = SealedProductType(pt).value
        sections.append(
            ft.Div(
                ft.H3(
                    label,
                    style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.12em; font-size:1.1rem; color:#475569; margin-bottom:12px; padding-top:16px; border-top:1px solid #111d30;",
                ),
                ft.Div(
                    *[sealed_product_tile(item, symbol, currency) for item in group],
                    cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3",
                ),
                cls="mb-8",
            )
        )

    return ft.Div(*sections, cls="p-4")
