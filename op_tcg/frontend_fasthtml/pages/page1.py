from fasthtml import ft

def page1_content():
    return ft.Div(
        ft.H1("Page 1", cls="text-3xl font-bold text-white"),
        ft.P("This is page 1", cls="text-gray-400"),
        cls="space-y-4"
    ) 