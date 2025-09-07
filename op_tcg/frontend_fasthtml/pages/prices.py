from fasthtml import ft
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner, create_skeleton_cards_indicator

HX_INCLUDE = "[name='currency'],[name='days'],[name='min_latest_price'],[name='max_latest_price'],[name='order_by'],[name='include_alt_art'],[name='change_metric']"

# Common CSS classes for select components (aligned with card popularity page)
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"


def create_filter_components(selected_currency: CardCurrency = CardCurrency.EURO, days: int = 30):
    return ft.Div(
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
                hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"
            ),
            cls="mb-4"
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
                hx_include=HX_INCLUDE, hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"
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
                hx_include=HX_INCLUDE+",[name='change_metric']", hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"
            ),
            cls="mb-2"
        ),
        ft.Div(
            ft.Label("Days", cls="block text-sm text-gray-300 mb-1"),
            ft.Input(type="number", min="1", max="365", value=str(days), name="days",
                     cls=SELECT_CLS,
                     hx_get="/api/price-overview", hx_trigger="change", hx_target="#price-overview",
                     hx_include=HX_INCLUDE, hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"),
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
                        hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"
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
                        hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"
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
            ft.Script(src="/public/js/double_range_slider.js"),
            ft.Link(rel="stylesheet", href="/public/css/double_range_slider.css"),
            cls="mb-4"
        ),
        ft.Div(
            ft.Label("Include Alt Art", cls="block text-sm text-gray-300 mb-1"),
            ft.Input(type="checkbox", name="include_alt_art", checked=False,
                     hx_get="/api/price-overview", hx_trigger="change", hx_target="#price-overview",
                     hx_include=HX_INCLUDE+",[name='include_alt_art']", hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper"),
            cls="mb-2"
        ),
        cls="space-y-4"
    )


def prices_page():
    return ft.Div(
        # Wrapper that receives htmx-request during requests so we can hide content reliably
        ft.Div(
            # Skeleton grid shown while HTMX requests are pending
            create_skeleton_cards_indicator(id="price-skeleton", count=15),
            ft.Div(
                hx_get="/api/price-overview",
                hx_trigger="load",
                hx_target="#price-overview",
                hx_swap="innerHTML",
                hx_include=HX_INCLUDE,
                hx_indicator="#price-loading-indicator, #price-skeleton, #price-loading-wrapper",
                id="price-overview",
                cls="min-h-screen htmx-hide-during-request"
            ),
            id="price-loading-wrapper"
        ),
        cls="p-0 lg:p-4"
    )


