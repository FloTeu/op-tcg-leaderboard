from fasthtml import ft
from .sidebar import sidebar

def layout(content, filter_component=None):
    return ft.Div(
        # Include external JavaScript file
        ft.Script(src="static/js/sidebar.js"),
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
            cls="fixed top-0 left-0 right-0 bg-gray-900",
            id="top-bar",
        ),
        sidebar(filter_component),
        ft.Div(
            content,
            cls="p-4 ml-64 min-h-screen bg-gray-900 transition-all duration-300 ease-in-out mt-16",
            id="main-content"
        ),
        cls="relative bg-gray-900"
    ) 