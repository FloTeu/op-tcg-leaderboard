from fasthtml import ft
from op_tcg.frontend_fasthtml.components.sidebar import sidebar

def layout(content, filter_component=None, current_path="/", canonical_url=None):
    """
    Main layout component that includes the sidebar navigation and content area.
    
    Args:
        content: The main content to display
        filter_component: Optional filter component to show in the sidebar
        current_path: The current path of the page, used for highlighting active navigation items
        canonical_url: The canonical URL for this page (for SEO)
    """
    # Generate canonical URL if not provided
    if canonical_url is None:
        base_url = "https://www.op-leaderboard.com"
        canonical_url = f"{base_url}{current_path}" if current_path != "/" else base_url
    
    # Create filter section if filter component is provided
    filter_section = None
    if filter_component:
        filter_section = ft.Div(
            ft.H3("Filters", cls="px-4 py-2 text-sm font-semibold text-gray-400 uppercase"),
            filter_component,
            cls="mt-6"
        )

    # Main layout
    return ft.Div(
        # SEO: Canonical URL for the current page
        ft.Link(rel="canonical", href=canonical_url),
        # Include external CSS files
        ft.Link(rel="stylesheet", href="public/css/leaderboard.css"),
        
        # Top bar that appears when sidebar is collapsed
        ft.Div(
            ft.Div(
                ft.Button(
                    ft.Div(
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white mb-1.5 transition-all duration-300"),
                        ft.Div(cls="w-6 h-0.5 bg-white transition-all duration-300"),
                        cls="flex flex-col justify-center items-center"
                    ),
                    cls="text-white hover:bg-gray-700 z-50 bg-gray-800 rounded-md p-2",
                    onclick="toggleSidebar()",
                    id="burger-menu"
                ),
                cls="flex items-center h-16 px-4"
            ),
            cls="fixed top-0 left-0 right-0 bg-gray-900 z-40 shadow-md",
            id="top-bar",
            style="display: block;"  # Start with top bar visible (mobile state)
        ),
        sidebar(filter_component, current_path),
        ft.Div(
            content,
            cls="p-4 min-h-screen bg-gray-900 transition-all duration-300 ease-in-out mt-16 relative",
            id="main-content",
            style="margin-left: 0;"  # Start with no left margin (mobile state)
        ),
        cls="relative bg-gray-900"
    ) 