from fasthtml import ft

def settings_content():
    return ft.Div(
        ft.H1("Settings", cls="text-3xl font-bold text-white"),
        ft.P("Manage your settings", cls="text-gray-400"),
        cls="space-y-4"
    ) 