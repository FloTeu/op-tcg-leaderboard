from fasthtml import ft
from .sidebar import sidebar

def layout(content):
    return ft.Div(
        sidebar(),
        ft.Div(
            content,
            cls="p-8 ml-64 min-h-screen bg-gray-900"
        ),
        cls="relative bg-gray-900"
    ) 