from fasthtml import ft

def tournaments_page():
    return ft.Div(
        ft.H1("Tournaments", cls="text-3xl font-bold text-white mb-6"),
        ft.P("Tournaments page coming soon...", cls="text-gray-300"),
        cls="min-h-screen"
    ) 