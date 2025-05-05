from fasthtml import ft

def create_nav_link(href: str, text: str, icon: str, is_active: bool = False) -> ft.A:
    """Create a navigation link with an icon."""
    active_classes = "bg-gray-800" if is_active else ""
    return ft.A(
        ft.Div(
            ft.Span(icon, cls="mr-3"),  # Icon
            ft.Span(text),  # Text
            cls=f"flex items-center px-4 py-2 text-gray-300 rounded-lg hover:bg-gray-700 {active_classes}"
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

def sidebar(filter_component=None, current_path="/"):
    """
    Create the sidebar with navigation and optional filter component.
    
    Args:
        filter_component: Optional filter component to show at the top of the sidebar
        current_path: Current active path for highlighting the active link
    """
    # Define navigation sections
    leader_links = [
        ("/", "Leaderboard", "🏆", current_path == "/"),
        ("/leader", "Leader", "👤", current_path == "/leader"),
        ("/tournaments", "Tournaments", "🏅", current_path == "/tournaments"),
        ("/card-movement", "Card Movement", "📈", current_path == "/card-movement"),
        ("/matchups", "Matchups", "🥊", current_path == "/matchups"),
    ]
    
    card_links = [
        ("/card-popularity", "Card Popularity", "💃", current_path == "/card-popularity"),
    ]
    
    support_links = [
        ("/bug-report", "Bug Report", "👾", current_path == "/bug-report"),
    ]
    
    return ft.Div(    
        
            # Burger menu
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
        # Navigation
        ft.Nav(
            create_nav_section("Leader", leader_links),
            create_nav_section("Card", card_links),
            create_nav_section("Support", support_links),
            cls="mt-6"
        ),
        # Filter component if provided
        filter_component if filter_component else "",
        cls="w-64 bg-gray-900 p-4 border-r border-gray-800 min-h-screen",
        id="sidebar"
    ) 