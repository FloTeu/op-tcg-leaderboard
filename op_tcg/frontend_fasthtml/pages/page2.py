from fasthtml import ft

def page2_content():
    return ft.Div(
        ft.H1("Page 2", cls="text-3xl font-bold text-white"),
        ft.P("This is page 2", cls="text-gray-400"),
        cls="space-y-4"
    ) 