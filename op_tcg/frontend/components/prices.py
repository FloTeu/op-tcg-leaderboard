from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, ExtendedCardData
from typing import List, Dict
from op_tcg.backend.models.input import MetaFormat
from op_tcg.frontend.utils.card_price import get_marketplace_link


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
