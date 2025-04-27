from fasthtml import ft

def home_page():
    return ft.Div(
        ft.H1("Home Page", cls="text-3xl font-bold text-white"),
        ft.P("Welcome to the home page", cls="text-gray-400"),
        cls="space-y-4"
    ) 