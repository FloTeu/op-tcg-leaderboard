from fasthtml import ft

def card_popularity_page():
    return ft.Div(
        ft.H1("Card Popularity", cls="text-3xl font-bold text-white mb-6"),
        ft.P("Card popularity analysis page coming soon...", cls="text-gray-300"),
        cls="min-h-screen"
    ) 