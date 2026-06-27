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


def sealed_product_tile(item: dict, symbol: str) -> ft.Div:
    name = item.get('name', '')
    product_type = SealedProductType(item.get('product_type', SealedProductType.PROMO))
    from_price = item.get('from_price')
    trend_price = item.get('trend_price')
    image_url = item.get('gcs_image_url') or item.get('image_url')
    url = item.get('url', '#')
    language = str(item.get('language', 'en')).upper()[:2]

    cfg = _SEALED_TYPE_CONFIG.get(product_type)
    from_str = f"{symbol}{from_price:.2f}" if from_price is not None else "—"
    trend_str = f"{symbol}{trend_price:.2f}" if trend_price is not None else "—"

    img_child = ft.Img(
        src=image_url, alt=name,
        style="position:absolute; top:0; left:0; width:100%; height:100%; object-fit:cover; display:block;",
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
            ft.A(
                "View on Cardmarket →",
                href=url, target="_blank", rel="noopener",
                style="font-family:'Barlow',sans-serif; font-size:0.7rem; color:#38bdf8; text-decoration:none; opacity:0.75; transition:opacity 0.12s;",
                onmouseover="this.style.opacity='1'",
                onmouseout="this.style.opacity='0.75'",
            ),
            cls="p-2",
        ),
        style="background:#0d1424; border:1px solid #1a2540; border-radius:8px; overflow:hidden; transition:border-color 0.15s, transform 0.15s;",
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
                    *[sealed_product_tile(item, symbol) for item in group],
                    cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3",
                ),
                cls="mb-8",
            )
        )

    return ft.Div(*sections, cls="p-4")
