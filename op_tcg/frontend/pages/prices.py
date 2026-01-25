from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend.components.loading import create_loading_spinner, create_skeleton_cards_indicator
from op_tcg.frontend.components.layout import create_mobile_filter_button
import time
from datetime import datetime, timedelta

HX_INCLUDE = "[name='currency'],[name='start_date'],[name='end_date'],[name='min_latest_price'],[name='max_latest_price'],[name='order_by'],[name='include_alt_art'],[name='change_metric'],[name='query']"

# Common CSS classes for select components (aligned with card popularity page)
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"
INPUT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500 placeholder-gray-400"
CHECKBOX_CLS = "w-5 h-5 text-blue-600 bg-gray-800 border-gray-600 rounded focus:ring-blue-500 focus:ring-2 focus:ring-offset-gray-800"


def create_filter_components(selected_currency: CardCurrency = CardCurrency.EURO, start_date: int = None, end_date: int = None):
    now = int(time.time())
    one_year_ago = int((datetime.now() - timedelta(days=365)).timestamp())

    if start_date is None:
        start_date = int((datetime.now() - timedelta(weeks=4)).timestamp())
    if end_date is None:
        end_date = now

    return ft.Div(
        ft.Div(
            ft.Label("Include Alt Art", cls="block text-sm text-gray-300 mb-1"),
            ft.Input(type="checkbox", name="include_alt_art", checked=False,
                     hx_get="/api/price-overview", hx_trigger="change", hx_target="#price-overview",
                     hx_include=HX_INCLUDE+",[name='include_alt_art']", hx_indicator="#price-loading-indicator",
                     cls=CHECKBOX_CLS),
            cls="mb-2"
        ),
        ft.Div(
            ft.Label("Order By", cls="block text-sm text-gray-300 mb-1"),
            ft.Select(
                ft.Option("Top Rising", value="rising", selected=True),
                ft.Option("Top Fallers", value="fallers"),
                ft.Option("Most Expensive", value="expensive"),
                id="price-order-by-select",
                name="order_by",
                cls=SELECT_CLS + " styled-select",
                hx_get="/api/price-overview", hx_trigger="change", hx_target="#price-overview",
                hx_include=HX_INCLUDE, hx_indicator="#price-loading-indicator"
            ),
            cls="mb-2"
        ),
        ft.Div(
            ft.Label("Change Metric", cls="block text-sm text-gray-300 mb-1"),
            ft.Select(
                ft.Option("Absolute", value="absolute", selected=True),
                ft.Option("Relative (%)", value="relative"),
                id="price-change-metric-select",
                name="change_metric",
                cls=SELECT_CLS + " styled-select",
                hx_get="/api/price-overview", hx_trigger="change", hx_target="#price-overview",
                hx_include=HX_INCLUDE+",[name='change_metric']", hx_indicator="#price-loading-indicator"
            ),
            cls="mb-2"
        ),
        ft.Div(
            ft.Label("Date Range", cls="block text-sm text-gray-300 mb-2"),
            ft.Div(
                ft.Div(
                    ft.Div(cls="slider-track"),
                    ft.Input(
                        type="range",
                        min=str(one_year_ago),
                        max=str(now),
                        value=str(start_date),
                        name="start_date",
                        cls="slider-range min-range",
                        hx_get="/api/price-overview",
                        hx_trigger="change",
                        hx_target="#price-overview",
                        hx_include=HX_INCLUDE,
                        hx_indicator="#price-loading-indicator"
                    ),
                    ft.Input(
                        type="range",
                        min=str(one_year_ago),
                        max=str(now),
                        value=str(end_date),
                        name="end_date",
                        cls="slider-range max-range",
                        hx_get="/api/price-overview",
                        hx_trigger="change",
                        hx_target="#price-overview",
                        hx_include=HX_INCLUDE,
                        hx_indicator="#price-loading-indicator"
                    ),
                    ft.Div(
                        ft.Span(cls="min-value text-white"),
                        ft.Span(" - ", cls="text-white mx-2"),
                        ft.Span(cls="max-value text-white"),
                        cls="slider-values"
                    ),
                    cls="double-range-slider",
                    id="date-range-slider",
                    data_double_range_slider="true",
                    data_type="date"
                ),
                cls="relative w-full"
            ),
            cls="mb-4"
        ),
        ft.Div(
            ft.Label("Price Range", cls="block text-sm text-gray-300 mb-2"),
            ft.Div(
                ft.Div(
                    ft.Div(cls="slider-track"),
                    ft.Input(
                        type="range",
                        min="0",
                        max="500",
                        value="0",
                        name="min_latest_price",
                        cls="slider-range min-range",
                        hx_get="/api/price-overview",
                        hx_trigger="change",
                        hx_target="#price-overview",
                        hx_include=HX_INCLUDE,
                        hx_indicator="#price-loading-indicator"
                    ),
                    ft.Input(
                        type="range",
                        min="0",
                        max="500",
                        value="500",
                        name="max_latest_price",
                        cls="slider-range max-range",
                        hx_get="/api/price-overview",
                        hx_trigger="change",
                        hx_target="#price-overview",
                        hx_include=HX_INCLUDE,
                        hx_indicator="#price-loading-indicator"
                    ),
                    ft.Div(
                        ft.Span("0", cls="min-value text-white"),
                        ft.Span(" - ", cls="text-white mx-2"),
                        ft.Span("500", cls="max-value text-white"),
                        cls="slider-values"
                    ),
                    cls="double-range-slider",
                    id="price-range-slider",
                    data_double_range_slider="true"
                ),
                cls="relative w-full"
            ),
            cls="mb-4"
        ),
        ft.Div(
            ft.Select(
                ft.Option("EUR", value=CardCurrency.EURO, selected=(selected_currency == CardCurrency.EURO)),
                ft.Option("USD", value=CardCurrency.US_DOLLAR, selected=(selected_currency == CardCurrency.US_DOLLAR)),
                label="Currency",
                id="price-currency-select",
                name="currency",
                cls=SELECT_CLS + " styled-select",
                hx_get="/api/price-overview",
                hx_trigger="change",
                hx_target="#price-overview",
                hx_include=HX_INCLUDE,
                hx_indicator="#price-loading-indicator"
            ),
            cls="mb-4"
        ),
        cls="space-y-4"
    )


def prices_page():
    return ft.Div(
        create_mobile_filter_button(),
        ft.Div(id="prices-header-container"),
        ft.Div(
            ft.Label("Search Cards", cls="text-white font-medium block mb-2"),
            ft.Input(
                type="search",
                name="query",
                placeholder="Search card name or ID...",
                cls=INPUT_CLS + " mb-4",
                hx_get="/api/price-overview",
                hx_trigger="keyup changed delay:500ms, search",
                hx_target="#price-overview",
                hx_include=HX_INCLUDE,
                hx_indicator="#price-loading-indicator"
            ),
            cls="w-full mx-0 mb-2"
        ),
        create_loading_spinner(
            id="price-loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),
        ft.Div(
            hx_get="/api/price-overview",
            hx_trigger="load",
            hx_target="#price-overview",
            hx_swap="innerHTML",
            hx_include=HX_INCLUDE,
            hx_indicator="#price-loading-indicator",
            id="price-overview",
            cls="min-h-screen"
        ),
        cls="p-0 lg:p-4"
    )
