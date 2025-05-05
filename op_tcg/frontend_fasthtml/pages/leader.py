from fasthtml import ft

def leader_page():
    return ft.Div(
        ft.H1("Leader Details", cls="text-3xl font-bold text-white mb-6"),
        ft.P("Leader details page coming soon...", cls="text-gray-300"),
        cls="min-h-screen"
    ) 