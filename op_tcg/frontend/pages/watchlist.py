from fasthtml import ft
from op_tcg.backend.db import get_watchlist
from op_tcg.frontend.components.watchlist_toggle import create_watchlist_toggle
from op_tcg.frontend.utils.card_price import get_marketplace_link
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

    # Determine View Mode
    view_mode = request.query_params.get("view", "list")
    sort_by = request.query_params.get("sort", "name")
    sort_order = request.query_params.get("order", "asc")

    # Prepare data for rendering (needed for both views to support sorting/prices)
    prepared_items = []

    for item in watchlist:
        card_id = item.get('card_id')
        version_val = item.get('card_version', 0)
        try:
             aa_version = int(version_val) if version_val != 'Base' else 0
        except:
             aa_version = 0
        language = item.get('language', 'en')

        # Data Lookup
        card_details = None
        if card_id in card_lookup:
            card_details = card_lookup[card_id].get(aa_version)
            if not card_details:
                card_details = card_lookup[card_id].get(0)
                if not card_details and card_lookup[card_id]:
                        card_details = next(iter(card_lookup[card_id].values()))

        card_name = getattr(card_details, 'name', 'Unknown Card') if card_details else card_id
        image_url = getattr(card_details, 'image_url', '') if card_details else ''
        latest_eur = getattr(card_details, 'latest_eur_price', 0.0) if card_details else 0.0
        latest_usd = getattr(card_details, 'latest_usd_price', 0.0) if card_details else 0.0

        # Ensure prices are floats
        if latest_eur is None: latest_eur = 0.0
        if latest_usd is None: latest_usd = 0.0

        item_data = {
            'card_id': card_id,
            'aa_version': aa_version,
            'language': language,
            'card_details': card_details,
            'card_name': card_name,
            'image_url': image_url,
            'latest_eur': latest_eur,
            'latest_usd': latest_usd
        }
        prepared_items.append(item_data)

    # Sort items
    reverse = (sort_order == 'desc')
    if sort_by == 'price':
        prepared_items.sort(key=lambda x: x['latest_usd'], reverse=reverse)
    else: # name
        prepared_items.sort(key=lambda x: x['card_name'], reverse=reverse)

    # Create View Switcher
    view_switcher = ft.Div(
        ft.A(
            ft.I(cls="fas fa-th-large mr-2"),
            "Grid",
            href="?view=list",
            cls=f"px-4 py-2 rounded-l-lg border border-gray-600 {'bg-blue-600 text-white' if view_mode == 'list' else 'bg-gray-800 text-gray-400 hover:bg-gray-700'} flex items-center transition-colors text-sm font-medium"
        ),
        ft.A(
            ft.I(cls="fas fa-table mr-2"),
            "Table",
            href="?view=table",
            cls=f"px-4 py-2 rounded-r-lg border border-gray-600 border-l-0 {'bg-blue-600 text-white' if view_mode == 'table' else 'bg-gray-800 text-gray-400 hover:bg-gray-700'} flex items-center transition-colors text-sm font-medium"
        ),
        cls="flex items-center"
    )

    content = None

    if view_mode == 'table':
        # Helpers for sort links
        def sort_link(label, column):
            icon = ""
            new_order = "asc"
            if sort_by == column:
                if sort_order == "asc":
                    icon = "fa-sort-up"
                    new_order = "desc"
                else:
                    icon = "fa-sort-down"
                    new_order = "asc"
            else:
                icon = "fa-sort text-gray-600"

            return ft.A(
                ft.Span(label),
                ft.I(cls=f"fas {icon} ml-1"),
                href=f"?view=table&sort={column}&order={new_order}",
                cls="flex items-center cursor-pointer hover:text-white transition-colors"
            )

        # Render Table View
        rows = []
        for item in prepared_items:
            card_id = item['card_id']
            aa_version = item['aa_version']
            language = item['language']
            card_details = item['card_details']
            card_name = item['card_name']
            image_url = item['image_url']

            # Marketplace Links
            if card_details:
                cm_url, _ = get_marketplace_link(card_details, CardCurrency.EURO)
                tcg_url, _ = get_marketplace_link(card_details, CardCurrency.US_DOLLAR)
            else:
                cm_url = f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={card_id}"
                tcg_url = f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={card_id}"

            version_label = "Base" if aa_version == 0 else f"Ver. {aa_version}"
            if aa_version > 0:
                 version_label = f"Alt Art {aa_version}"

            chart_id = f"chart-table-{card_id}-{aa_version}-{language}"

            toggle_btn = create_watchlist_toggle(
                card_id=card_id,
                card_version=aa_version,
                language=language,
                is_in_watchlist=True,
                include_script=(len(rows) == 0),
                btn_cls="bg-transparent hover:bg-gray-700 p-2 rounded-full"
            )

            rows.append(
                ft.Tr(
                    # Card Info
                    ft.Td(
                        ft.Div(
                            ft.Img(src=image_url, cls="w-16 h-auto rounded shadow-sm mr-4 cursor-pointer hover:opacity-80 transition-opacity flex-shrink-0",
                                   alt=card_name,
                                   hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                   hx_target="body",
                                   hx_swap="beforeend"),
                            ft.Div(
                                ft.Div(card_name, cls="font-bold text-white text-base cursor-pointer hover:text-blue-400 whitespace-normal break-words line-clamp-2",
                                       hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                       hx_target="body",
                                       hx_swap="beforeend"),
                                ft.Div(f"{card_id}", cls="text-sm text-gray-400"),
                                cls="flex flex-col min-w-0"
                            ),
                            cls="flex items-center"
                        ),
                        cls="px-4 py-3 align-top"
                    ),
                    # Latest Price
                    ft.Td(
                        ft.Div(
                            ft.A(
                                ft.Span(f"€{item['latest_eur']:.2f}", cls="font-bold text-gray-200 group-hover:text-blue-400 transition-colors mr-2 text-sm"),
                                ft.Span("CM", cls="text-[10px] bg-blue-600/20 text-blue-300 group-hover:bg-blue-600 group-hover:text-white px-1.5 py-0.5 rounded transition-colors"),
                                href=cm_url,
                                target="_blank",
                                cls="flex items-center justify-end group cursor-pointer hover:bg-gray-700/50 rounded px-2 py-1 transition-colors mb-1 w-full"
                            ),
                            ft.A(
                                ft.Span(f"${item['latest_usd']:.2f}", cls="font-bold text-gray-200 group-hover:text-green-400 transition-colors mr-2 text-sm"),
                                ft.Span("TCG", cls="text-[10px] bg-green-600/20 text-green-300 group-hover:bg-green-600 group-hover:text-white px-1.5 py-0.5 rounded transition-colors"),
                                href=tcg_url,
                                target="_blank",
                                cls="flex items-center justify-end group cursor-pointer hover:bg-gray-700/50 rounded px-2 py-1 transition-colors w-full"
                            ),
                            cls="flex flex-col items-end min-w-[100px]"
                        ),
                        cls="px-4 py-3 whitespace-nowrap align-middle"
                    ),
                    # Details
                    ft.Td(
                        ft.Div(
                            ft.Div(version_label, cls="text-sm text-gray-300"),
                            ft.Div(language, cls="text-xs text-gray-500 uppercase"),
                            cls="flex flex-col"
                        ),
                        cls="px-4 py-3 whitespace-nowrap align-middle"
                    ),
                    # Actions
                    ft.Td(
                        ft.Div(
                            toggle_btn,
                            cls="flex items-center justify-center pl-2"
                        ),
                        cls="px-4 py-3 whitespace-nowrap align-middle"
                    ),
                    # Price Chart
                    ft.Td(
                        ft.Div(
                            # Absolute positioned time selector
                            ft.Select(
                                ft.Option("30d", value="30"),
                                ft.Option("90d", value="90", selected=True),
                                ft.Option("180d", value="180"),
                                ft.Option("1y", value="365"),
                                ft.Option("All", value="1000"),
                                name="days",
                                id=f"price-period-selector-table-{chart_id}",
                                cls="absolute top-1 right-1 z-10 bg-gray-800 text-white border border-gray-600 rounded px-1 py-0 text-[10px] focus:ring-blue-500 focus:border-blue-500 block cursor-pointer hover:bg-gray-700 transition-colors opacity-100 placeholder-transparent appearance-none text-center min-w-[34px]",
                                hx_get="/api/card-price-development-chart",
                                hx_target=f"#{chart_id}",
                                hx_indicator=f"#{chart_id}-loading",
                                hx_vals=f'{{"card_id": "{card_id}", "aa_version": "{aa_version}", "include_alt_art": "false", "compact": "true"}}', # Ensure compact stays true
                                hx_on__before_request=f"document.getElementById('{chart_id}').innerHTML = ''; document.getElementById('{chart_id}-loading').classList.remove('hidden');"
                            ),
                            ft.Div(
                                id=chart_id,
                                hx_get=f"/api/card-price-development-chart?card_id={card_id}&days=90&aa_version={aa_version}&compact=true",
                                hx_trigger="revealed",
                                hx_indicator=f"#{chart_id}-loading",
                                cls="w-full h-32"
                            ),
                            create_loading_spinner(
                                id=f"{chart_id}-loading",
                                size="w-6 h-6",
                                container_classes="absolute inset-0 flex items-center justify-center h-32 pointer-events-none hidden"
                            ),
                            cls="w-full min-w-[200px] h-32 bg-gray-900/30 rounded relative overflow-hidden group"
                        ),
                        cls="px-4 py-2 w-full align-middle"
                    ),
                    cls="bg-gray-800 border-b border-gray-700 hover:bg-gray-750 transition-colors watchlist-card-item"
                )
            )

        content = ft.Div(
            ft.Table(
                ft.Thead(
                    ft.Tr(
                        ft.Th(sort_link("Card", "name"), cls="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-1/3 min-w-[250px]"),
                        ft.Th(sort_link("Latest Price", "price"), cls="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap w-28"),
                        ft.Th("Version", cls="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider whitespace-nowrap w-24"),
                        ft.Th("Actions", cls="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider w-24"),
                        ft.Th("Price Trend (90d)", cls="px-4 py-3 text-left text-xs font-medium text-gray-400 uppercase tracking-wider min-w-[300px]"),
                    ),
                    cls="bg-gray-900"
                ),
                ft.Tbody(
                    *rows,
                    cls="divide-y divide-gray-700"
                ),
                cls="min-w-full divide-y divide-gray-700"
            ),
            cls="overflow-x-auto rounded-lg shadow-lg border border-gray-700"
        )

    else:
        # LIST VIEW (Existing Logic)
        items = []
        for item in prepared_items:
            card_id = item['card_id']
            aa_version = item['aa_version']
            language = item['language']
            card_details = item['card_details']
            card_name = item['card_name']
            image_url = item['image_url']

            # Generate marketplace links
            if card_details:
                cm_url, _ = get_marketplace_link(card_details, CardCurrency.EURO)
                tcg_url, _ = get_marketplace_link(card_details, CardCurrency.US_DOLLAR)
            else:
                cm_url = f"https://www.cardmarket.com/en/OnePiece/Products/Search?searchString={card_id}"
                tcg_url = f"https://www.tcgplayer.com/search/one-piece-card-game/product?q={card_id}"

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
                        # Header: Image + Details + Toggle (Flex Row)
                        ft.Div(
                             # Image
                            ft.Div(
                                 ft.Img(src=image_url, cls="w-16 sm:w-20 h-auto rounded shadow-sm hover:opacity-100 transition-opacity",
                                        alt=card_name),
                                 cls="flex-shrink-0 mr-4 cursor-pointer",
                                 hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                 hx_target="body",
                                 hx_swap="beforeend"
                            ),
                            # Title + Meta
                            ft.Div(
                                ft.H3(card_name, cls="text-xl font-bold text-white hover:text-blue-400 transition-colors"),
                                ft.P(f"{card_id} • {version_label} • {language}", cls="text-sm text-gray-400 mt-1"),
                                # Check if prices exist and display them
                                ft.Div(
                                    ft.Span(f"€{item['latest_eur']:.2f}", cls="text-sm font-bold text-blue-400 mr-3"),
                                    ft.Span(f"${item['latest_usd']:.2f}", cls="text-sm font-bold text-green-400"),
                                    cls="mt-1"
                                ),
                                cls="flex-1 min-w-0 pr-4 cursor-pointer", # min-w-0 for truncate text if needed
                                hx_get=f"/api/card-modal?card_id={card_id}&meta_format=latest&aa_version={aa_version}",
                                hx_target="body",
                                hx_swap="beforeend"
                            ),
                            # Toggle
                            ft.Div(
                                toggle_btn,
                                cls="flex-shrink-0"
                            ),
                            cls="flex items-start mb-0"
                        ),

                        # Content Area: Chart Only (Full Width)
                        ft.Div(
                            # Control Bar (Time Range Selector)
                            ft.Div(
                                ft.Select(
                                    ft.Option("30 Days", value="30"),
                                    ft.Option("90 Days", value="90", selected=True),
                                    ft.Option("180 Days", value="180"),
                                    ft.Option("1 Year", value="365"),
                                    ft.Option("All Time", value="1000"),
                                    name="days", # Send value as 'days' parameter
                                    id=f"price-period-selector-{chart_id}",
                                    cls="bg-gray-700 text-white border border-gray-600 rounded px-2 py-0.5 text-xs focus:ring-blue-500 focus:border-blue-500 block cursor-pointer hover:bg-gray-600 transition-colors",
                                    hx_get="/api/card-price-development-chart",
                                    hx_target=f"#{chart_id}",
                                    hx_indicator=f"#{chart_id}-loading",
                                    hx_vals=f'{{"card_id": "{card_id}", "aa_version": "{aa_version}", "include_alt_art": "false"}}',
                                    hx_on__before_request=f"document.getElementById('{chart_id}').innerHTML = ''; document.getElementById('{chart_id}-loading').classList.remove('hidden');"
                                ),
                                cls="flex justify-end pr-1 pt-1"
                            ),
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
                                    container_classes="absolute inset-0 flex items-center justify-center h-48 sm:h-64 pointer-events-none hidden"
                                ),
                                cls="w-full min-w-0 bg-gray-900/50 rounded p-0 mt-0 relative"
                            ),

                            # Marketplace Buttons
                            ft.Div(
                                ft.Div(
                                    ft.A(
                                        "Cardmarket",
                                        href=cm_url,
                                        target="_blank",
                                        rel="noopener",
                                        cls="flex-1 text-center px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-l-lg transition-colors border-r border-blue-800",
                                    ),
                                    ft.A(
                                        "TCGPlayer",
                                        href=tcg_url,
                                        target="_blank",
                                        rel="noopener",
                                        cls="flex-1 text-center px-4 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-medium rounded-r-lg transition-colors",
                                    ),
                                    cls="flex w-full"
                                ),
                                cls="mt-3"
                            ),
                            cls="w-full mt-2"
                        ),
                        cls="watchlist-card-item bg-gray-800 p-4 sm:p-6 rounded-lg shadow-lg border border-gray-700 hover:border-gray-600 transition-colors"
                    )
                )
            )

        content = ft.Div(
            *items,
            cls="grid grid-cols-1 gap-6"
        )

    return ft.Div(
        ft.Div(
            ft.H1("My Watchlist", cls="text-2xl font-bold text-white"),
            view_switcher,
            cls="flex justify-between items-center mb-6"
        ),
        content,
        cls="container mx-auto px-4 py-8"
    )

