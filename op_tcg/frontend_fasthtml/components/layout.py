from fasthtml import ft
from op_tcg.frontend_fasthtml.components.sidebar import sidebar

def layout(content, filter_component=None):
    """
    Main layout component that includes the sidebar navigation and content area.
    
    Args:
        content: The main content to display
        filter_component: Optional filter component to show in the sidebar
    """
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
        # Include external CSS files
        ft.Link(rel="stylesheet", href="static/css/leaderboard.css"),
        # Include external JavaScript file
        ft.Script(src="static/js/sidebar.js"),
        ft.Div(
            sidebar(filter_component=filter_section),
            ft.Main(
                content,
                cls="flex-1 p-8"
            ),
            cls="flex"
        ),
        cls="min-h-screen bg-gray-900"
    ) 