from fasthtml import ft

def bug_report_page():
    return ft.Div(
        ft.H1("Bug Report", cls="text-3xl font-bold text-white mb-6"),
        ft.P("Bug report page coming soon...", cls="text-gray-300"),
        cls="min-h-screen"
    ) 