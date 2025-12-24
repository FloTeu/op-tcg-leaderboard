from fasthtml import ft
from starlette.requests import Request

from op_tcg.frontend.api.models import PriceOverviewParams
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.extract import (
    get_price_change_data,
    get_top_current_prices,
)
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend.components.prices import price_tiles
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup


def _header(currency: CardCurrency, days: int) -> ft.Div:
    return ft.Div(
        ft.H2("Card Prices Overview", cls="text-2xl font-bold text-white mb-1"),
        ft.P(
            f"Last {days} days • Currency: {'EUR' if currency == CardCurrency.EURO else 'USD'}",
            cls="text-gray-300"
        ),
        cls="mb-4"
    )


def setup_api_routes(rt):
    @rt("/api/price-overview")
    def price_overview(request: Request):
        params = PriceOverviewParams(**get_query_params_as_dict(request))

        items: list[dict]
        if params.order_by == "rising":
            items = get_price_change_data(
                params.days, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="DESC", include_alt_art=params.include_alt_art, change_metric=params.change_metric
            )
        elif params.order_by == "fallers":
            items = get_price_change_data(
                params.days, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="ASC", include_alt_art=params.include_alt_art, change_metric=params.change_metric
            )
        else:  # expensive
            items = get_top_current_prices(
                params.currency,
                params.page,
                params.max_results,
                params.min_latest_price,
                params.max_latest_price,
                direction="DESC",
                language='en',
                include_alt_art=params.include_alt_art
            )

        # Pagination (infinite scroll)
        # Detect if there is a next page by fetching one extra row
        has_more = len(items) > params.max_results
        page_items = items[:params.max_results]

        # Provide card metadata for building marketplace URLs (set info)
        card_lookup = get_card_id_card_data_lookup()
        content = price_tiles(page_items, params.currency, card_lookup)

        if params.page == 1:
            # First page returns header + container with infinite scroll trigger
            return ft.Div(
                _header(params.currency, params.days),
                ft.Div(
                    content,
                    ft.Div(
                        id="prices-infinite-scroll-trigger",
                        hx_get=f"/api/price-overview?page={params.page + 1}",
                        hx_trigger="revealed",
                        hx_target="#prices-grid-container",
                        hx_swap="beforeend",
                        hx_include="[name='currency'],[name='days'],[name='min_latest_price'],[name='max_latest_price'],[name='max_results'],[name='order_by'],[name='change_metric'],[name='include_alt_art']",
                        cls="h-10"
                    ) if has_more else None,
                    id="prices-grid-container",
                    cls="p-4"
                )
            )

        # Subsequent pages return only tiles and a new trigger
        return ft.Div(
            content,
            ft.Div(
                id="prices-infinite-scroll-trigger",
                hx_get=f"/api/price-overview?page={params.page + 1}",
                hx_trigger="revealed",
                hx_target="#prices-grid-container",
                hx_swap="beforeend",
                hx_include="[name='currency'],[name='days'],[name='min_latest_price'],[name='max_latest_price'],[name='max_results'],[name='order_by'],[name='change_metric'],[name='include_alt_art']",
                cls="h-10"
            ) if has_more else None,
        )


