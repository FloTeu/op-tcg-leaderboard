from fasthtml import ft


def create_nav_link(href: str, text: str, icon: str, is_active: bool = False) -> ft.A:
    """Create a navigation link with an icon."""
    active_classes = "bg-gray-700 text-white font-semibold border-l-4 border-blue-500" if is_active else "text-gray-300 hover:bg-gray-700"
    return ft.A(
        ft.Div(
            ft.Span(icon, cls="mr-3"),  # Icon
            ft.Span(text),  # Text
            cls=f"flex items-center px-4 py-2 rounded-lg {active_classes}"
        ),
        href=href,
        cls="block"
    )

def create_nav_section(title: str, links: list[tuple[str, str, str, bool]]) -> ft.Div:
    """Create a navigation section with a title and links."""
    return ft.Div(
        ft.H3(title, cls="px-4 py-2 text-sm font-semibold text-gray-400 uppercase"),
        *[create_nav_link(href, text, icon, is_active) for href, text, icon, is_active in links],
        cls="mb-6"
    )

def sidebar_content(filter_component=None, current_path="/", persist_query: dict | None = None):
    # Helper to build href with optional persisted query params
    def build_href(base_path: str) -> str:
        if not persist_query:
            return base_path
        # Map region param for leader page
        query_params = {}
        if persist_query.get("region"):
            query_params["region"] = persist_query.get("region")
        if persist_query.get("meta_format"):
            query_params["meta_format"] = persist_query.get("meta_format")
        if not query_params:
            return base_path
        qp = "&".join([f"{k}={v}" for k, v in query_params.items() if v is not None and v != ""])
        return f"{base_path}?{qp}" if qp else base_path

    # Define navigation sections with persisted params
    leader_links = [
        (build_href("/"), "Leaderboard", "🏆", current_path == "/"),
        (build_href("/leader"), "Leader", "👤", current_path == "/leader"),
        (build_href("/tournaments"), "Tournaments", "🏅", current_path == "/tournaments"),
        (build_href("/card-movement"), "Card Movement", "📈", current_path == "/card-movement"),
        (build_href("/matchups"), "Matchups", "🥊", current_path == "/matchups"),
    ]
    
    card_links = [
        (build_href("/card-popularity"), "Card Popularity", "💃", current_path == "/card-popularity"),
        #(build_href("/prices"), "Card Prices", "💰", current_path == "/prices"),
    ]
    
    support_links = [
        (build_href("/bug-report"), "Bug Report", "👾", current_path == "/bug-report"),
    ]

    return ft.Div(
        # Navigation sections
        create_nav_section("Leader", leader_links),
        create_nav_section("Card", card_links),
        create_nav_section("Support", support_links),
        # Filter section
        ft.Div(
            ft.H2("Filters", cls="text-xl font-bold text-white mb-4") if filter_component else None,
            filter_component if filter_component else None,
            cls="mt-4"
        ) if filter_component else None,
        cls="space-y-2"
    )

def sidebar(filter_component=None, current_path="/", persist_query: dict | None = None):
    return ft.Div(
        ft.Div(
            ft.Div(
                ft.H2("Navigation", cls="text-xl font-bold text-white"),
                ft.Button(
                    ft.Div(
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white transition-all duration-300"),
                        cls="flex flex-col justify-center items-center"
                    ),
                    cls="text-white hover:bg-gray-700 z-50 bg-gray-800 rounded-md p-2",
                    onclick="toggleSidebar()",
                    id="sidebar-burger-menu"
                ),
                cls="flex justify-between items-center mb-4"
            ),
            sidebar_content(filter_component, current_path, persist_query),
            cls="p-4"
        ),
        cls="fixed left-0 top-0 h-full w-80 bg-gray-800 overflow-y-auto scrollbar-thin scrollbar-thumb-gray-600 scrollbar-track-gray-800 hover:scrollbar-thumb-gray-500 z-50 shadow-lg",
        id="sidebar",
        style="transform: translateX(-100%);"  # Start closed on mobile
    ) 