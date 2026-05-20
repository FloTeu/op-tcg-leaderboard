from fasthtml import ft
from op_tcg.backend.models.input import MetaFormat
from op_tcg.backend.models.cards import OPTcgColor, OPTcgCardCatagory, OPTcgAbility, CardCurrency, OPTcgAttribute, OPTcgCardRarity
from op_tcg.frontend.components.loading import create_loading_spinner, create_skeleton_cards_indicator
from op_tcg.frontend.components.layout import create_mobile_filter_button
from op_tcg.frontend.utils.extract import get_card_popularity_data, get_card_id_card_data_lookup
from op_tcg.backend.models.cards import ExtendedCardData

HX_INCLUDE = "[name='meta_format'],[name='card_colors'],[name='card_attributes'],[name='card_counter'],[name='card_category'],[name='card_types'],[name='currency'],[name='min_price'],[name='max_price'],[name='min_cost'],[name='max_cost'],[name='min_power'],[name='max_power'],[name='card_abilities'],[name='card_rarity'],[name='ability_text'],[name='filter_operator'],[name='search_term'],[name='release_meta_format']"
FILTER_HX_ATTRS = {
    "hx_get": "/api/card-popularity",
    "hx_trigger": "change",
    "hx_target": "#card-popularity-content",
    "hx_include": HX_INCLUDE,
    "hx_indicator": "#card-popularity-loading-indicator"
}


def _styles() -> ft.Style:
    return ft.Style("""
.cp-page { font-family: 'Barlow', sans-serif; }

/* Shared design-token panel/select/label classes (mirrors meta.py) */
.meta-panel {
    background: #0d1424;
    border: 1px solid #1a2540;
    border-radius: 12px;
    padding: 20px;
}
@media (min-width: 768px) { .meta-panel { padding: 24px 28px; } }

.meta-select {
    width: 100%;
    background: #080e1c;
    color: #f1f5f9;
    border: 1px solid #1a2540;
    border-radius: 8px;
    padding: 8px 12px;
    font-family: 'Barlow', sans-serif;
    font-size: 0.875rem;
    outline: none;
    cursor: pointer;
    transition: border-color 0.15s, box-shadow 0.15s;
}
.meta-select:focus { border-color: #38bdf8; box-shadow: 0 0 0 2px rgba(56,189,248,0.08); }
.meta-select::placeholder { color: #1e2d45; }

.meta-section-label {
    font-family: 'Bebas Neue', sans-serif;
    letter-spacing: 0.1em;
    color: #334155;
    font-size: 0.65rem;
    text-transform: uppercase;
    display: block;
    margin-bottom: 6px;
}

.slider-values {
    font-family: 'Share Tech Mono', monospace;
    font-size: 0.8rem;
    color: #38bdf8;
}

/* Card item */
.cp-card-item {
    border-radius: 8px;
    overflow: hidden;
    border: 1px solid #1a2540;
    transition: transform 0.18s cubic-bezier(0.34,1.56,0.64,1), border-color 0.15s;
}
.cp-card-item:hover {
    transform: translateY(-4px) scale(1.02);
    border-color: #2d3f5a;
}

.cp-card-info {
    background: #0d1424;
    padding: 10px 10px 8px;
}

.cp-progress-container {
    width: 100%;
    height: 16px;
    background: #080e1c;
    border: 1px solid #1a2540;
    border-radius: 8px;
    overflow: hidden;
}
.cp-progress-bar {
    height: 100%;
    background: linear-gradient(90deg, #0ea5e9, #38bdf8);
    display: flex;
    align-items: center;
    justify-content: flex-end;
    padding-right: 4px;
    transition: width 0.3s ease;
    border-radius: 8px;
}
""")


def create_filter_components(selected_meta_format: MetaFormat | None = None, currency: CardCurrency | None = None):
    selected_meta_format = selected_meta_format or MetaFormat.latest_meta_format()
    currency = currency or CardCurrency.EURO

    meta_format_select = ft.Div(
        ft.Span("Meta Format", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(mf, value=mf, selected=mf == selected_meta_format) for mf in reversed(MetaFormat.to_list())],
            id="meta-format-select",
            name="meta_format",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS
        ),
    )

    release_meta_format_select = ft.Div(
        ft.Span("Release Meta", cls="meta-section-label"),
        ft.Select(
            ft.Option("Any", value="", selected=True),
            *[ft.Option(mf, value=mf) for mf in reversed(MetaFormat.to_list())],
            id="release-meta-format-select",
            name="release_meta_format",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS
        ),
    )

    card_colors_select = ft.Div(
        ft.Span("Card Colors", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(color, value=color, selected=True) for color in OPTcgColor.to_list()],
            id="card-colors-select",
            name="card_colors",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **FILTER_HX_ATTRS
        ),
    )

    card_attributes_select = ft.Div(
        ft.Span("Card Attributes", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(attr, value=attr) for attr in OPTcgAttribute.to_list()],
            id="card-attributes-select",
            name="card_attributes",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **FILTER_HX_ATTRS
        ),
    )

    card_counter_select = ft.Div(
        ft.Span("Counter", cls="meta-section-label"),
        ft.Select(
            ft.Option("Any", value="", selected=True),
            *[ft.Option(str(val), value=str(val)) for val in [0, 1000, 2000]],
            id="card-counter-select",
            name="card_counter",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS
        ),
    )

    card_type_select = ft.Div(
        ft.Span("Card Type", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(cat, value=cat, selected=cat != OPTcgCardCatagory.LEADER)
              for cat in OPTcgCardCatagory.to_list()],
            id="card-type-select",
            name="card_category",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **FILTER_HX_ATTRS
        ),
    )

    card_subtype_wrapper = ft.Div(
        create_loading_spinner(id="card-subtype-loading", size="w-4 h-4", container_classes="min-h-[60px]"),
        id="card-subtype-wrapper",
        hx_get="/api/card-subtype-select",
        hx_trigger="load",
        hx_swap="innerHTML"
    )

    currency_select = ft.Div(
        ft.Span("Currency", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(curr, value=curr, selected=(curr == currency))
              for curr in [CardCurrency.EURO, CardCurrency.US_DOLLAR]],
            id="currency-select",
            name="currency",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS
        ),
    )

    def _slider(label: str, slider_id: str, name_min: str, name_max: str,
                min_val: str, max_val: str) -> ft.Div:
        return ft.Div(
            ft.Span(label, cls="meta-section-label"),
            ft.Div(
                ft.Div(cls="slider-track"),
                ft.Input(type="range", min=min_val, max=max_val, value=min_val,
                         name=name_min, cls="slider-range min-range", **FILTER_HX_ATTRS),
                ft.Input(type="range", min=min_val, max=max_val, value=max_val,
                         name=name_max, cls="slider-range max-range", **FILTER_HX_ATTRS),
                ft.Div(
                    ft.Span(min_val, cls="min-value"),
                    ft.Span(" – ", style="color:#334155; margin:0 4px;"),
                    ft.Span(max_val, cls="max-value"),
                    cls="slider-values",
                ),
                cls="double-range-slider",
                id=slider_id,
                data_double_range_slider="true",
            ),
        )

    price_range_slider = _slider("Card Price Range", "price-range-slider", "min_price", "max_price", "0", "80")
    cost_range_slider  = _slider("Card Cost Range",  "cost-range-slider",  "min_cost",  "max_cost",  "0", "10")
    power_range_slider = _slider("Card Power (k)",   "power-range-slider", "min_power", "max_power", "0", "15")

    card_abilities_select = ft.Div(
        ft.Span("Card Abilities", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(ability, value=ability) for ability in OPTcgAbility.to_list()],
            id="card-abilities-select",
            name="card_abilities",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **FILTER_HX_ATTRS
        ),
    )

    card_rarity_select = ft.Div(
        ft.Span("Card Rarity", cls="meta-section-label"),
        ft.Select(
            *[ft.Option(rarity, value=rarity) for rarity in OPTcgCardRarity.to_list()],
            id="card-rarity-select",
            name="card_rarity",
            multiple=True,
            size=1,
            cls="meta-select multiselect",
            **FILTER_HX_ATTRS
        ),
    )

    ability_text_input = ft.Div(
        ft.Span("Ability Text", cls="meta-section-label"),
        ft.Input(
            type="text",
            name="ability_text",
            placeholder="Search in ability text...",
            cls="meta-select",
            **FILTER_HX_ATTRS
        ),
    )

    filter_operator_select = ft.Div(
        ft.Span("Filter Operator", cls="meta-section-label"),
        ft.Select(
            ft.Option("AND", value="AND", selected=True),
            ft.Option("OR", value="OR"),
            id="filter-operator-select",
            name="filter_operator",
            cls="meta-select styled-select",
            **FILTER_HX_ATTRS
        ),
    )

    return ft.Div(
        meta_format_select,
        release_meta_format_select,
        card_colors_select,
        card_attributes_select,
        card_counter_select,
        card_type_select,
        card_subtype_wrapper,
        currency_select,
        price_range_slider,
        cost_range_slider,
        power_range_slider,
        card_abilities_select,
        card_rarity_select,
        ability_text_input,
        filter_operator_select,
        cls="space-y-4"
    )


def create_card_popularity_content(cards_data: list[ExtendedCardData], card_popularities: dict[str, float],
                                   page: int = 1, search_term: str = None,
                                   currency: CardCurrency = CardCurrency.EURO):
    """Create the card popularity content with a grid of cards and popularity bars."""
    if not cards_data:
        return ft.Div(
            ft.P("No cards found matching the criteria.",
                 style="font-family:'Barlow',sans-serif; color:#475569; text-align:center; padding:32px 0;"),
            cls="min-h-[200px] flex items-center justify-center"
        )

    CARDS_PER_PAGE = 30
    start_idx = (page - 1) * CARDS_PER_PAGE
    end_idx = start_idx + CARDS_PER_PAGE
    current_page_cards = cards_data[start_idx:end_idx]
    has_more = end_idx < len(cards_data)

    card_grid = ft.Div(
        *[
            ft.Div(
                ft.Div(
                    ft.Img(
                        src=card.image_url,
                        alt=card.name,
                        cls="w-full h-auto cursor-pointer",
                        hx_get=f"/api/card-modal?card_id={card.id}",
                        hx_include=HX_INCLUDE,
                        hx_target="body",
                        hx_swap="beforeend"
                    ),
                    cls="relative",
                ),
                ft.Div(
                    ft.Div(
                        ft.Span(
                            card.name,
                            style="font-family:'Barlow',sans-serif; font-weight:500; font-size:0.78rem; color:#f1f5f9; display:block; margin-bottom:4px;"
                        ),
                        ft.Span(
                            (f"{card.latest_eur_price:.2f} €" if currency == CardCurrency.EURO else f"${card.latest_usd_price:.2f}")
                            if (currency == CardCurrency.EURO and card.latest_eur_price) or
                               (currency == CardCurrency.US_DOLLAR and card.latest_usd_price)
                            else "N/A",
                            style="font-family:'Share Tech Mono',monospace; font-size:0.7rem; color:#475569;"
                        ),
                        cls="flex justify-between items-start mb-3",
                    ),
                    ft.Div(
                        ft.Div(
                            ft.Span(
                                f"{int(card_popularities.get(card.id, 0) * 100)}%",
                                style="font-family:'Share Tech Mono',monospace; font-size:0.65rem; color:#f1f5f9; padding-right:4px;"
                            ),
                            cls="cp-progress-bar",
                            style=f"width:{max(card_popularities.get(card.id, 0) * 100, 4)}%;",
                            data_tooltip="Percentage of same color decks playing this card.",
                        ),
                        cls="cp-progress-container",
                    ),
                    cls="cp-card-info",
                ),
                cls="cp-card-item",
            )
            for card in current_page_cards
        ],
        cls="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-3",
    )

    loading_spinner = create_loading_spinner(
        id="card-popularity-batch-loading", size="w-6 h-6", container_classes="min-h-[50px]"
    )
    skeleton = create_skeleton_cards_indicator(id="card-popularity-batch-skeleton", count=16)

    infinite_trigger = ft.Div(
        id="infinite-scroll-trigger",
        hx_get=f"/api/card-popularity?page={page + 1}",
        hx_trigger="revealed",
        hx_target="#card-grid-container",
        hx_swap="beforeend",
        hx_include=HX_INCLUDE,
        hx_indicator="#card-popularity-batch-loading, #card-popularity-batch-skeleton",
        cls="h-10"
    ) if has_more else None

    if page == 1:
        return ft.Div(
            card_grid,
            infinite_trigger,
            skeleton,
            loading_spinner,
            id="card-grid-container",
            cls="w-full",
        )

    # Subsequent pages: only the new batch + updated trigger
    return ft.Div(
        card_grid,
        infinite_trigger,
        skeleton,
        loading_spinner,
    )


def card_popularity_page():
    return ft.Div(
        _styles(),
        ft.Div(
            # Page header
            ft.Div(
                ft.H1("CARD POPULARITY",
                      style="font-family:'Bebas Neue',sans-serif; letter-spacing:0.1em; font-size:2rem; color:#f1f5f9; line-height:1; margin-bottom:6px;"),
                ft.P(
                    "Cards ordered by play rate. 100% means the card appears in every tournament deck of the same color.",
                    style="font-family:'Barlow',sans-serif; font-size:0.875rem; color:#334155;",
                ),
                cls="mb-6",
                style="padding-bottom:16px; border-bottom:1px solid #111d30;",
            ),
            create_mobile_filter_button(),
            # Search bar — always visible above content
            ft.Div(
                ft.Span("Search Cards", cls="meta-section-label"),
                ft.Input(
                    type="text",
                    name="search_term",
                    placeholder="Search by name, meta format, type etc. (e.g. 'OP09 Luffy')",
                    cls="meta-select",
                    **FILTER_HX_ATTRS
                ),
                cls="mb-4 mt-4",
            ),
            # Loading spinner — below search bar, above content
            create_loading_spinner(
                id="card-popularity-loading-indicator",
                size="w-8 h-8",
                container_classes="min-h-[80px]"
            ),
            # Content container
            ft.Div(
                id="card-popularity-content",
                cls="min-h-screen",
                hx_get="/api/card-popularity",
                hx_trigger="load",
                hx_include=HX_INCLUDE,
                hx_indicator="#card-popularity-loading-indicator"
            ),
            cls="cp-page bg-deep-navy px-4 py-4 md:px-6 md:py-6 min-h-screen",
            style="max-width:1280px; margin:0 auto;",
        ),
        # JavaScript for initialization sequence and URL-based modal
        ft.Script("""
            let initializationComplete = false;
            let initialLoadDone = false;

            document.addEventListener('htmx:configRequest', function(evt) {
                if (!initializationComplete && evt.target.classList.contains('slider-range')) {
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

            function checkAndOpenCardModal() {
                const url = new URL(window.location);
                const cardId = url.searchParams.get('card_id');
                if (cardId) {
                    const urlWithoutCardId = new URL(window.location);
                    urlWithoutCardId.searchParams.delete('card_id');
                    window.originalUrlBeforeModal = urlWithoutCardId.href;
                    const checkContentLoaded = setInterval(() => {
                        const cardGridContainer = document.getElementById('card-grid-container');
                        if (cardGridContainer) {
                            clearInterval(checkContentLoaded);
                            const metaFormat = document.querySelector('[name="meta_format"]')?.value || 'latest';
                            const currency = document.querySelector('[name="currency"]')?.value || 'eur';
                            fetch(`/api/card-modal?card_id=${cardId}&meta_format=${metaFormat}&currency=${currency}`)
                                .then(response => response.text())
                                .then(html => {
                                    document.body.insertAdjacentHTML('beforeend', html);
                                    htmx.process(document.body);
                                })
                                .catch(error => console.error('Error loading card modal:', error));
                        }
                    }, 100);
                    setTimeout(() => clearInterval(checkContentLoaded), 5000);
                }
            }

            document.addEventListener('htmx:afterSettle', function(evt) {
                if (evt.target.id === 'card-subtype-wrapper') {
                    triggerInitialLoad();
                    setTimeout(() => { initializationComplete = true; }, 500);
                }
                if (evt.target.id === 'card-popularity-content') {
                    checkAndOpenCardModal();
                }
            });

            document.addEventListener('DOMContentLoaded', function() {
                setTimeout(() => { triggerInitialLoad(); }, 500);
                setTimeout(() => { initializationComplete = true; }, 2000);
            });
        """)
    )
