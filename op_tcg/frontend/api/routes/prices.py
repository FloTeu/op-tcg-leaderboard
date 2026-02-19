from fasthtml import ft
from starlette.requests import Request
import time
from datetime import datetime, timedelta

from op_tcg.frontend.api.models import PriceOverviewParams
from op_tcg.frontend.utils.api import get_query_params_as_dict
from op_tcg.frontend.utils.extract import (
    get_price_change_data,
)
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend.components.prices import price_tiles
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup, get_card_lookup_by_id_and_aa
from op_tcg.frontend.components.loading import create_loading_spinner, create_skeleton_cards_indicator


def _header(currency: CardCurrency, start_date: int, end_date: int) -> ft.Div:
    start_str = datetime.fromtimestamp(start_date).strftime('%Y-%m-%d')
    end_str = datetime.fromtimestamp(end_date).strftime('%Y-%m-%d')
    return ft.Div(
        ft.H2("Card Prices Overview", cls="text-2xl font-bold text-white mb-1"),
        ft.P(
            f"From {start_str} to {end_str} • Currency: {'EUR' if currency == CardCurrency.EURO else 'USD'}",
            cls="text-gray-300"
        ),
        cls="mb-4",
        id="prices-header-container",
        hx_swap_oob="true"
    )


def setup_api_routes(rt):
    @rt("/api/price-overview")
    def price_overview(request: Request):
        params = PriceOverviewParams(**get_query_params_as_dict(request))

        # Default dates if not provided
        if not params.start_date:
             params.start_date = int((datetime.now() - timedelta(weeks=4)).timestamp())
        if not params.end_date:
             params.end_date = int(time.time())

        items: list[dict]
        if params.order_by == "rising":
            items = get_price_change_data(
                params.start_date, params.end_date, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="DESC", include_alt_art=params.include_alt_art, change_metric=params.change_metric, query_text=params.query, sort_by="change", rarity=params.rarity
            )
        elif params.order_by == "fallers":
            items = get_price_change_data(
                params.start_date, params.end_date, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="ASC", include_alt_art=params.include_alt_art, change_metric=params.change_metric, query_text=params.query, sort_by="change", rarity=params.rarity
            )
        elif params.order_by == "diff_eur_high":
             items = get_price_change_data(
                params.start_date, params.end_date, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="DESC", include_alt_art=params.include_alt_art, change_metric=params.change_metric, query_text=params.query, sort_by="diff_eur_high", rarity=params.rarity
            )
        elif params.order_by == "diff_usd_high":
             items = get_price_change_data(
                params.start_date, params.end_date, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="DESC", include_alt_art=params.include_alt_art, change_metric=params.change_metric, query_text=params.query, sort_by="diff_usd_high", rarity=params.rarity
            )
        else:  # expensive
            items = get_price_change_data(
                params.start_date, params.end_date, params.currency, params.min_latest_price, params.max_latest_price, params.page, params.max_results, order_dir="DESC", include_alt_art=params.include_alt_art, change_metric=params.change_metric, query_text=params.query, sort_by="price", rarity=params.rarity
            )

        # Pagination (infinite scroll)
        # Detect if there is a next page by fetching one extra row
        has_more = len(items) > params.max_results
        page_items = items[:params.max_results]

        # Provide card metadata for building marketplace URLs (set info)
        card_lookup = get_card_lookup_by_id_and_aa()
        content = price_tiles(page_items, params.currency, card_lookup)

        # Create loading spinner and skeleton for new batches
        loading_spinner = create_loading_spinner(
            id="price-batch-loading",
            size="w-6 h-6",
            container_classes="min-h-[50px]"
        )
        # Skeleton only for newly loaded batches
        skeleton = create_skeleton_cards_indicator(id="price-batch-skeleton", count=15)

        if params.page == 1:
            # First page returns header (OOB) + container with infinite scroll trigger
            return ft.Div(
                _header(params.currency, params.start_date, params.end_date),
                ft.Div(
                    content,
                    ft.Div(
                        id="prices-infinite-scroll-trigger",
                        hx_get=f"/api/price-overview?page={params.page + 1}",
                        hx_trigger="revealed",
                        hx_target="this",
                        hx_swap="outerHTML",
                        hx_include="[name='currency'],[name='start_date'],[name='end_date'],[name='min_latest_price'],[name='max_latest_price'],[name='max_results'],[name='order_by'],[name='change_metric'],[name='include_alt_art'],[name='query'],[name='rarity']",
                        hx_indicator="#price-batch-loading, #price-batch-skeleton",
                        cls="h-10"
                    ) if has_more else None,
                    skeleton,
                    loading_spinner,
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
                hx_target="this",
                hx_swap="outerHTML",
                hx_include="[name='currency'],[name='start_date'],[name='end_date'],[name='min_latest_price'],[name='max_latest_price'],[name='max_results'],[name='order_by'],[name='change_metric'],[name='include_alt_art'],[name='query'],[name='rarity']",
                hx_indicator="#price-batch-loading, #price-batch-skeleton",
                cls="h-10"
            ) if has_more else None
        )
