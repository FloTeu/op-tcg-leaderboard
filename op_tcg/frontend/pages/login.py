from fasthtml import ft


def login_provider_select_content() -> ft.Div:
    return ft.Div(
        ft.Div(
            ft.H1("Sign In", cls="text-2xl font-bold text-white mb-2 text-center"),
            ft.P("Choose how you'd like to sign in", cls="text-gray-400 text-sm text-center mb-8"),
            ft.A(
                ft.I(cls="fab fa-google mr-3"),
                "Continue with Google",
                href="/login/google",
                cls="flex items-center justify-center w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors mb-3"
            ),
            ft.A(
                ft.I(cls="fab fa-discord mr-3"),
                "Continue with Discord",
                href="/login/discord",
                cls="flex items-center justify-center w-full px-6 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold rounded-lg transition-colors"
            ),
            cls="bg-gray-800 rounded-xl p-8 border border-gray-700 max-w-sm w-full mx-auto shadow-2xl"
        ),
        cls="container mx-auto px-4 py-16 flex justify-center"
    )
