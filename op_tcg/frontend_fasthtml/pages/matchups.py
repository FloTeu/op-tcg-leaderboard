from fasthtml import ft

def matchups_page():
    return ft.Div(
        ft.H1("Leader Matchups", cls="text-3xl font-bold text-white mb-6"),
        ft.P("Leader matchup analysis page coming soon...", cls="text-gray-300"),
        cls="min-h-screen"
    ) 