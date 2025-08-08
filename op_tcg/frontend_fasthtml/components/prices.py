from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency
from typing import List
from op_tcg.backend.models.input import MetaFormat


def price_tile(item: dict, currency: CardCurrency, card_elements: list[str]) -> ft.Div:
    symbol = "€" if currency == CardCurrency.EURO else "$"
    name = item.get('name') or item.get('card_id')
    latest = item.get('latest_price') or 0
    pct_change = item.get('pct_change')
    abs_change = item.get('abs_change')
    is_up = (pct_change or 0) > 0
    change_bg = "bg-green-800/50" if is_up else ("bg-red-800/50" if (pct_change or 0) < 0 else "bg-gray-700/60")
    change_txt = "text-green-300" if is_up else ("text-red-300" if (pct_change or 0) < 0 else "text-gray-300")
    arrow = "▲" if is_up else ("▼" if (pct_change or 0) < 0 else "→")
    pct_str = f"{pct_change*100:.1f}%" if pct_change is not None else "—"
    abs_str = f"{symbol}{abs_change:.2f}" if abs_change is not None else "—"
    card_id = item.get('card_id')

    latest_meta = MetaFormat.latest_meta_format()

    local_indicator_id = f"price-modal-indicator-{card_id}"
    image = ft.Img(
        src=item.get('image_url'), alt=name,
        cls="w-full h-auto rounded-t-lg cursor-pointer hover:opacity-90 transition-opacity",
        hx_get=f"/api/card-modal?card_id={card_id}&meta_format={latest_meta}&card_elements={'&card_elements='.join(card_elements)}",
        hx_include="[name='currency']",
        hx_target="body", hx_swap="beforeend",
        hx_indicator=f"#{local_indicator_id}"
    )

    # Footer with clear price and change chips
    title = ft.H3(name, cls="text-white text-sm font-semibold truncate")
    price_row = ft.Div(
        ft.Span(f"{symbol}{latest:.2f}", cls="text-white font-semibold text-base"),
        ft.Span(f"{arrow} {abs_str} ({pct_str})", cls=f"text-xs md:text-sm font-semibold px-2 py-1 rounded-full {change_bg} {change_txt}"),
        cls="flex items-center justify-between gap-2 mt-1"
    )

    return ft.Div(
        ft.Div(
            image,
            # Local, tiny indicator so global skeleton/spinner are not used for modal requests
            ft.Div(id=local_indicator_id, cls="htmx-indicator", style="display:none;"),
        ),
        ft.Div(title, price_row, cls="p-2"),
        cls="bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow"
    )


def price_tiles(items: List[dict], currency: CardCurrency) -> ft.Div:
    card_elements = [it.get('card_id') for it in items if it.get('card_id')]
    tile_grid_cls = "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4"
    return ft.Div(
        ft.Div(*[price_tile(it, currency, card_elements) for it in items], cls=tile_grid_cls)
    )


