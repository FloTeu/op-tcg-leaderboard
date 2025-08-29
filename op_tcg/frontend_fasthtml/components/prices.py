from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency, ExtendedCardData
from typing import List, Dict, Any
from op_tcg.backend.models.input import MetaFormat
from urllib.parse import quote_plus


def price_tile(item: dict, currency: CardCurrency, card_elements: list[str], card_id2card_data: Dict[str, ExtendedCardData] | None = None) -> ft.Div:
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

    # External marketplace link based on currency and card id/name
    # Build vendor-specific query. For Cardmarket use card_id; for TCGplayer use name + set code/name when available
    if currency == CardCurrency.EURO:
        query = quote_plus(card_id or name)
    else:
        q_str = f"{name} "
        if card_id2card_data and card_id in card_id2card_data:
            q_str = f"{name} {card_id2card_data[card_id].release_set_name}".strip()
        query = quote_plus(q_str)
    external_link = ft.A(
        "View on Cardmarket" if currency == CardCurrency.EURO else "View on TCGplayer",
        href=(f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={query}&category=-1&mode=gallery" if currency == CardCurrency.EURO
              else f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={query}&productLineName=one-piece-card-game"),
        target="_blank",
        rel="noopener",
        cls="text-blue-300 text-xs hover:underline"
    )

    return ft.Div(
        ft.Div(
            image,
            # Local, tiny indicator so global skeleton/spinner are not used for modal requests
            ft.Div(id=local_indicator_id, cls="htmx-indicator", style="display:none;"),
        ),
        ft.Div(title, price_row, ft.Div(external_link, cls="mt-1 flex justify-end"), cls="p-2"),
        cls="bg-gray-800 rounded-lg shadow hover:shadow-lg transition-shadow"
    )


def price_tiles(items: List[dict], currency: CardCurrency, card_id2card_data: Dict[str, ExtendedCardData] | None = None) -> ft.Div:
    card_elements = [it.get('card_id') for it in items if it.get('card_id')]
    tile_grid_cls = "grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4"
    return ft.Div(
        ft.Div(*[price_tile(it, currency, card_elements, card_id2card_data) for it in items], cls=tile_grid_cls)
    )


