from fasthtml import ft
from op_tcg.backend.db import get_watchlist
from op_tcg.frontend.components.watchlist_toggle import create_watchlist_toggle
from op_tcg.frontend.utils.extract import get_card_id_card_data_lookup, get_card_lookup_by_id_and_aa
from op_tcg.frontend.components.loading import create_loading_spinner
from op_tcg.backend.models.cards import CardCurrency

def watchlist_page(request):
    user = request.session.get('user')
    if not user:
         return ft.Div(
             ft.H1("Access Denied", cls="text-2xl font-bold text-white mb-4"),
             ft.P("Please login to view your watchlist.", cls="text-gray-400"),
             cls="container mx-auto px-4 py-8"
         )

    user_id = user.get('sub')
    watchlist = get_watchlist(user_id)

    if not watchlist:
        return ft.Div(
            ft.H1("My Watchlist", cls="text-2xl font-bold text-white mb-4"),
            ft.P("Your watchlist is currently empty.", cls="text-gray-400"),
            cls="container mx-auto px-4 py-8"
        )

    # Get all card data to lookup details
    # Use nested lookup to find specific version details (image, name, etc.)
    card_lookup = get_card_lookup_by_id_and_aa()

    items = []
    for item in watchlist:
        card_id = item.get('card_id')
        # Handle version logic (stored as int 0, 1, etc or legacy string)
        version_val = item.get('card_version', 0)
        try:
             aa_version = int(version_val) if version_val != 'Base' else 0
        except:
             aa_version = 0

        language = item.get('language', 'en')

        # Lookup card details for specific version
        # card_lookup is dict[card_id][aa_version] -> ExtendedCardData
        card_details = None
        if card_id in card_lookup:
            # Try specific version, fallback to base (0), fallback to any
            card_details = card_lookup[card_id].get(aa_version)
            if not card_details:
                card_details = card_lookup[card_id].get(0)
                if not card_details and card_lookup[card_id]:
                    # taking first available if base not found
                     card_details = next(iter(card_lookup[card_id].values()))

        card_name = getattr(card_details, 'name', 'Unknown Card') if card_details else card_id
        image_url = getattr(card_details, 'image_url', '') if card_details else ''

        # Determine label for version
        version_label = "Base" if aa_version == 0 else f"Ver. {aa_version}"
        if aa_version > 0:
             version_label = f"Alt Art {aa_version}"

        # Create unique ID for chart container
        chart_id = f"chart-{card_id}-{aa_version}-{language}"

        toggle_btn = create_watchlist_toggle(
            card_id=card_id,
            card_version=aa_version,
            language=language,
            is_in_watchlist=True,
            include_script=(len(items) == 0)
        )

        items.append(
            ft.Div(
                ft.Div(
                    # Header with Card Info
                    ft.Div(
                        ft.Div(
                            ft.H3(card_name, cls="text-xl font-bold text-white"),
                            ft.P(f"{card_id} • {version_label} • {language}", cls="text-sm text-gray-400 mt-1"),
                            cls="flex-1"
                        ),
                        toggle_btn,
                        cls="flex justify-between items-start mb-4"
                    ),
                    # Content Area: Image + Chart
                    ft.Div(
                        # Image (condensed)
                        ft.Div(
                             ft.Img(src=image_url, cls="w-16 sm:w-24 h-auto rounded shadow-sm hover:opacity-100 transition-opacity",
                                    alt=card_name),
                             cls="flex-shrink-0 mr-4"
                        ),
                        # Chart Container
                        ft.Div(
                            ft.Div(
                                id=chart_id,
                                hx_get=f"/api/card-price-development-chart?card_id={card_id}&days=90&aa_version={aa_version}",
                                hx_trigger="revealed", # Load when scrolled into view
                                hx_indicator=f"#{chart_id}-loading",
                                cls="w-full h-48 sm:h-64"
                            ),
                            create_loading_spinner(
                                id=f"{chart_id}-loading",
                                size="w-8 h-8",
                                container_classes="h-48 sm:h-64 flex items-center justify-center"
                            ),
                            cls="flex-1 min-w-0 bg-gray-900/50 rounded p-2"
                        ),
                        cls="flex flex-row"
                    ),
                    cls="watchlist-card-item bg-gray-800 p-6 rounded-lg shadow-lg border border-gray-700 hover:border-gray-600 transition-colors"
                )
            )
        )

    return ft.Div(
        ft.H1("My Watchlist", cls="text-2xl font-bold text-white mb-6"),
        ft.Div(
            *items,
            cls="grid grid-cols-1 gap-6" # 1 column vertical stack for charts visibility
        ),
        cls="container mx-auto px-4 py-8"
    )

