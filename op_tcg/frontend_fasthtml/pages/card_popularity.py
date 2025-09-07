from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.cards import OPTcgColor, OPTcgCardCatagory, OPTcgAbility, CardCurrency, OPTcgAttribute
from op_tcg.frontend_fasthtml.components.loading import create_loading_spinner, create_skeleton_cards_indicator
from op_tcg.frontend_fasthtml.utils.extract import get_card_popularity_data, get_card_id_card_data_lookup
from op_tcg.backend.models.cards import ExtendedCardData

# Common HTMX attributes for filter components
HX_INCLUDE = "[name='meta_format'],[name='card_colors'],[name='card_attributes'],[name='card_counter'],[name='card_category'],[name='card_types'],[name='currency'],[name='min_price'],[name='max_price'],[name='min_cost'],[name='max_cost'],[name='min_power'],[name='max_power'],[name='card_abilities'],[name='ability_text'],[name='filter_operator'],[name='search_term']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/card-popularity",
    "hx_trigger": "change",
    "hx_target": "#card-popularity-content",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#card-popularity-loading-indicator"
}

# Common CSS classes for select components
SELECT_CLS = "w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg shadow-sm focus:ring-2 focus:ring-blue-500 focus:border-blue-500"

def create_filter_components():
    # Meta format select
    meta_format_select = ft.Select(
        label="Meta Format",
        id="meta-format-select",
        name="meta_format",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(mf, value=mf, selected=mf == MetaFormat.latest_meta_format()) for mf in reversed(MetaFormat.to_list())],
        **FILTER_HX_ATTRS
    )

    # Card colors multiselect
    card_colors_select = ft.Select(
        label="Card Colors",
        id="card-colors-select",
        name="card_colors",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(color, value=color, selected=True) for color in OPTcgColor.to_list()],
        **FILTER_HX_ATTRS
    )

    # Card attributes multiselect
    card_attributes_select = ft.Select(
        label="Card Attributes",
        id="card-attributes-select",
        name="card_attributes",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(attr, value=attr) for attr in OPTcgAttribute.to_list()],
        **FILTER_HX_ATTRS
    )

    # Card counter select
    card_counter_select = ft.Select(
        label="Counter",
        id="card-counter-select",
        name="card_counter",
        cls=SELECT_CLS + " styled-select",
        *[
            ft.Option("Any", value="", selected=True),
            *[ft.Option(str(val), value=str(val)) for val in [0, 1000, 2000]]
        ],
        **FILTER_HX_ATTRS
    )

    # Card type select
    card_type_select = ft.Select(
        label="Card Type",
        id="card-type-select",
        name="card_category",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[
            ft.Option(
                cat, 
                value=cat, 
                selected=cat != OPTcgCardCatagory.LEADER
            ) for cat in OPTcgCardCatagory.to_list()
        ],
        **FILTER_HX_ATTRS
    )

    # Card subtype multiselect - now loaded via HTMX
    card_subtype_wrapper = ft.Div(
        create_loading_spinner(
            id="card-subtype-loading",
            size="w-4 h-4",
            container_classes="min-h-[60px]"
        ),
        id="card-subtype-wrapper",
        hx_get="/api/card-subtype-select",
        hx_trigger="load",
        hx_swap="innerHTML"
    )

    # Currency select
    currency_select = ft.Select(
        label="Currency",
        id="currency-select",
        name="currency",
        cls=SELECT_CLS + " styled-select",
        *[ft.Option(curr, value=curr) for curr in [CardCurrency.EURO, CardCurrency.US_DOLLAR]],
        **FILTER_HX_ATTRS
    )

    # Price range slider
    price_range_slider = ft.Div(
        ft.Label("Card Price Range", cls="text-white font-medium block mb-2"),
        ft.Div(
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(
                    type="range",
                    min="0",
                    max="80",
                    value="0",
                    name="min_price",
                    cls="slider-range min-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Input(
                    type="range",
                    min="0",
                    max="80",
                    value="80",
                    name="max_price",
                    cls="slider-range max-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Div(
                    ft.Span("0", cls="min-value text-white"),
                    ft.Span(" - ", cls="text-white mx-2"),
                    ft.Span("80", cls="max-value text-white"),
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
        cls="mb-6"
    )

    # Cost range slider
    cost_range_slider = ft.Div(
        ft.Label("Card Cost Range", cls="text-white font-medium block mb-2"),
        ft.Div(
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(
                    type="range",
                    min="0",
                    max="10",
                    value="0",
                    name="min_cost",
                    cls="slider-range min-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Input(
                    type="range",
                    min="0",
                    max="10",
                    value="10",
                    name="max_cost",
                    cls="slider-range max-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Div(
                    ft.Span("0", cls="min-value text-white"),
                    ft.Span(" - ", cls="text-white mx-2"),
                    ft.Span("10", cls="max-value text-white"),
                    cls="slider-values"
                ),
                cls="double-range-slider",
                id="cost-range-slider",
                data_double_range_slider="true"
            ),
            cls="relative w-full"
        ),
        cls="mb-6"
    )

    # Power range slider
    power_range_slider = ft.Div(
        ft.Label("Card Power Range (in k)", cls="text-white font-medium block mb-2"),
        ft.Div(
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(
                    type="range",
                    min="0",
                    max="15",
                    value="0",
                    name="min_power",
                    cls="slider-range min-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Input(
                    type="range",
                    min="0",
                    max="15",
                    value="15",
                    name="max_power",
                    cls="slider-range max-range",
                    **FILTER_HX_ATTRS
                ),
                ft.Div(
                    ft.Span("0", cls="min-value text-white"),
                    ft.Span(" - ", cls="text-white mx-2"),
                    ft.Span("15", cls="max-value text-white"),
                    cls="slider-values"
                ),
                cls="double-range-slider",
                id="power-range-slider",
                data_double_range_slider="true"
            ),
            cls="relative w-full"
        ),
        cls="mb-6"
    )

    # Card abilities multiselect
    card_abilities_select = ft.Select(
        label="Card Abilities",
        id="card-abilities-select",
        name="card_abilities",
        multiple=True,
        size=1,
        cls=SELECT_CLS + " multiselect",
        *[ft.Option(ability, value=ability) for ability in OPTcgAbility.to_list()],
        **FILTER_HX_ATTRS
    )

    # Ability text input
    ability_text_input = ft.Div(
        ft.Label("Ability Text", cls="text-white font-medium block mb-2"),
        ft.Input(
            type="text",
            name="ability_text",
            placeholder="Search in ability text...",
            cls="w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg",
            **FILTER_HX_ATTRS
        ),
        cls="mb-6"
    )

    # Filter operator select
    filter_operator_select = ft.Select(
        label="Filter Operator",
        id="filter-operator-select",
        name="filter_operator",
        cls=SELECT_CLS + " styled-select",
        *[
            ft.Option("AND", value="AND", selected=True),
            ft.Option("OR", value="OR")
        ],
        **FILTER_HX_ATTRS
    )

    return ft.Div(
        meta_format_select,
        card_colors_select,
        card_attributes_select,
        card_counter_select,
        card_type_select,
        card_subtype_wrapper,  # Now uses HTMX loading
        currency_select,
        price_range_slider,
        cost_range_slider,
        power_range_slider,
        card_abilities_select,
        ability_text_input,
        filter_operator_select,
        cls="space-y-4"
    )

def create_card_popularity_content(cards_data: list[ExtendedCardData], card_popularities: dict[str, float], page: int = 1, search_term: str = None, currency: CardCurrency = CardCurrency.EURO):
    """Create the card popularity content with a grid of cards and popularity bars.
    
    Args:
        cards_data: List of card data objects
        card_popularities: Dictionary mapping card IDs to their popularity (0-1)
        page: Current page number (1-based)
        search_term: Current search term
        currency: Selected currency for price display
    """
    # Search bar
    search_bar = ft.Div(
        ft.Label("Search Cards", cls="text-white font-medium block mb-2"),
        ft.Input(
            type="text",
            name="search_term",
            placeholder="Search by name, type, release meta etc. (use ';' to combine conditions)",
            cls="w-full p-3 bg-gray-800 text-white border-gray-600 rounded-lg",
            value=search_term,
            **FILTER_HX_ATTRS
        ),
        cls="mb-6"
    )

    if not cards_data:
        return ft.Div(
            search_bar,
            ft.Div(
                ft.P("No cards found matching the criteria.", cls="text-gray-300"),
                cls="min-h-[200px] flex items-center justify-center"
            )
        )

    CARDS_PER_PAGE = 30
    start_idx = (page - 1) * CARDS_PER_PAGE
    end_idx = start_idx + CARDS_PER_PAGE
    current_page_cards = cards_data[start_idx:end_idx]
    has_more = end_idx < len(cards_data)

    # Create card grid
    card_grid = ft.Div(
        *[
            ft.Div(
                # Card image
                ft.Div(
                    ft.Img(
                        src=card.image_url,
                        alt=card.name,
                        cls="w-full h-auto rounded-lg cursor-pointer hover:opacity-90 transition-opacity",
                        hx_get=f"/api/card-modal?card_id={card.id}&card_elements={'&card_elements='.join([c.id for c in current_page_cards])}",
                        hx_include=HX_INCLUDE,
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="relative"
                ),
                # Card name, price and popularity bar
                ft.Div(
                    # Name and price container
                    ft.Div(
                        # Card name
                        ft.H3(
                            card.name,
                            cls="text-white font-medium break-words"
                        ),
                        # Price information
                        ft.Div(
                            ft.Span(
                                f"{card.latest_eur_price:.2f} €" if currency == CardCurrency.EURO else f"${card.latest_usd_price:.2f}",
                                cls="text-white text-sm font-medium whitespace-nowrap"
                            ) if (currency == CardCurrency.EURO and card.latest_eur_price) or (currency == CardCurrency.US_DOLLAR and card.latest_usd_price) else
                            ft.Span(
                                "Price N/A",
                                cls="text-gray-400 text-sm whitespace-nowrap"
                            ),
                            cls="ml-2"
                        ),
                        cls="flex justify-between items-start mb-2"
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span(
                                f"{int(card_popularities.get(card.id, 0) * 100)}%",
                                cls="text-white text-sm ml-5"
                            ),
                            cls="progress-bar",
                            style=f"width: {max(card_popularities.get(card.id, 0) * 100, 5)}%",
                            data_tooltip="Percentage of same color decks playing this card."
                        ),
                        cls="progress-container"
                    ),
                    cls="p-3 bg-gray-800 rounded-b-lg"
                ),
                cls="card-grid-item"
            )
            for card in current_page_cards
        ],
        cls="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4"
    )

    # Add CSS for the card grid and progress bars
    styles = ft.Style("""
        .card-grid-item {
            transition: transform 0.2s;
        }
        .card-grid-item:hover {
            transform: translateY(-5px);
        }
        .progress-container {
            width: 100%;
            height: 20px;
            background-color: #374151;
            border-radius: 10px;
            overflow: hidden;
        }
        .progress-bar {
            height: 100%;
            background-color: #10B981;
            display: flex;
            align-items: center;
            justify-content: center;
            transition: width 0.3s ease;
        }
    """)

    # Create loading spinner and skeleton for new batches
    loading_spinner = create_loading_spinner(
        id="card-popularity-batch-loading",
        size="w-6 h-6",
        container_classes="min-h-[50px]"
    )
    # Skeleton only for newly loaded batches
    skeleton = create_skeleton_cards_indicator(id="card-popularity-batch-skeleton", count=16)

    # For the first page, return the full structure
    if page == 1:
        return ft.Div(
            styles,
            ft.Div(
                search_bar,
                card_grid,
                # Add infinite scroll trigger at the bottom
                ft.Div(
                    id="infinite-scroll-trigger",
                    hx_get=f"/api/card-popularity?page={page + 1}",
                    hx_trigger="revealed",
                    hx_target="#card-grid-container",
                    hx_swap="beforeend",
                    hx_include=HX_INCLUDE,
                    hx_indicator="#card-popularity-batch-loading, #card-popularity-batch-skeleton",
                    cls="h-10"
                ) if has_more else None,
                skeleton,
                loading_spinner,
                id="card-grid-container",
                cls="p-4"
            )
        )
    
    # For subsequent pages, only return the new cards and a new trigger
    return ft.Div(
        card_grid,
        # Add new trigger that will replace the old one
        ft.Div(
            id="infinite-scroll-trigger",
            hx_get=f"/api/card-popularity?page={page + 1}",
            hx_trigger="revealed",
            hx_target="#card-grid-container",
            hx_swap="beforeend",
            hx_include=HX_INCLUDE,
            hx_indicator="#card-popularity-batch-loading, #card-popularity-batch-skeleton",
            cls="h-10"
        ) if has_more else None,
        skeleton,
        loading_spinner
    )

def card_popularity_page():
    return ft.Div(
        ft.H1("Card Popularity", cls="text-3xl font-bold text-white mb-6"),
        ft.P("A list of cards ordered by popularity. A popularity of 100% stands for 100% occurrence in tournament decks of the same card color.", cls="text-gray-300 mb-8"),
        # Loading spinner
        create_loading_spinner(
            id="card-popularity-loading-indicator",
            size="w-8 h-8",
            container_classes="min-h-[100px]"
        ),
        # Content container that will be loaded via HTMX
        ft.Div(
            id="card-popularity-content",
            cls="min-h-screen",
            hx_get="/api/card-popularity",
            hx_trigger="load",
            hx_indicator="#card-popularity-loading-indicator"
        ),
        # JavaScript to handle card subtype loading sequence
        ft.Script("""
            let initializationComplete = false;
            let initialLoadDone = false;
            
            // Prevent HTMX during initialization
            document.addEventListener('htmx:configRequest', function(evt) {
                // Block range slider HTMX requests during initialization
                if (!initializationComplete && 
                    evt.target.classList.contains('slider-range')) {
                    evt.preventDefault();
                    return false;
                }
            });
            
            function triggerInitialLoad() {
                if (!initialLoadDone) {
                    initialLoadDone = true;
                    htmx.trigger('#card-popularity-content', 'load');
                }
            }
            
            document.addEventListener('htmx:afterSettle', function(evt) {
                if (evt.target.id === 'card-subtype-wrapper') {
                    // After card subtype loads, trigger content loading
                    triggerInitialLoad();
                    
                    // Allow range sliders to work after a short delay
                    setTimeout(() => {
                        initializationComplete = true;
                    }, 500);
                }
            });
            
            // Backup to enable range sliders and ensure content loads
            document.addEventListener('DOMContentLoaded', function() {
                // Backup initial load in case card subtype loads too quickly
                setTimeout(() => {
                    triggerInitialLoad();
                }, 500);
                
                // Backup to enable range sliders
                setTimeout(() => {
                    initializationComplete = true;
                }, 2000);
            });
        """)
    ) 