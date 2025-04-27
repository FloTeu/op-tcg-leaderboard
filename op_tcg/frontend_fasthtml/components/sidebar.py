from fasthtml import ft
from shad4fast import *

def sidebar():
    return ft.Div(
        ft.Div(
            ft.H2("Navigation", cls="text-xl font-bold mb-4 text-white"),
            ft.Div(
                Button("Home", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/'"),
                Button("Page 1", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/page1'"),
                Button("Page 2", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/page2'"),
                Button("Settings", variant="ghost", cls="w-full justify-start text-white hover:bg-gray-700", onclick="window.location.href='/settings'"),
                cls="space-y-2"
            ),
            cls="p-4"
        ),
        cls="w-64 bg-gray-800 h-screen fixed left-0 top-0"
    ) 