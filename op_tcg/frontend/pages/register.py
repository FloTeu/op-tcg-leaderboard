from fasthtml import ft


def register_content(pending_user: dict, csrf_token: str) -> ft.Div:
    name = pending_user.get('name', 'there')
    email = pending_user.get('email', '')
    picture = pending_user.get('picture')

    avatar = (
        ft.Img(src=picture, cls="w-16 h-16 rounded-full mx-auto mb-4")
        if picture else
        ft.Div(name[0].upper(),
               cls="w-16 h-16 rounded-full bg-blue-600 flex items-center justify-center text-white text-2xl font-bold mx-auto mb-4")
    )

    provider = pending_user.get('provider', 'google')
    provider_label = 'Google' if provider == 'google' else 'Discord'
    provider_icon_cls = 'fab fa-google' if provider == 'google' else 'fab fa-discord'

    return ft.Div(
        ft.Div(
            avatar,
            ft.H1("Create Your Account", cls="text-2xl font-bold text-white mb-2 text-center"),
            ft.P(f"Sign in as {name}", cls="text-gray-300 text-center mb-1"),
            ft.P(email, cls="text-gray-500 text-sm text-center mb-1"),
            ft.P(
                ft.I(cls=f"{provider_icon_cls} mr-1"),
                f"via {provider_label}",
                cls="text-gray-500 text-xs text-center mb-6"
            ),
            ft.P(
                "You don't have an account yet. Would you like to create one?",
                cls="text-gray-400 text-sm text-center mb-8"
            ),
            ft.Form(
                ft.Input(type="hidden", name="csrf_token", value=csrf_token),
                ft.Button(
                    ft.I(cls="fas fa-user-plus mr-2"),
                    "Create Account",
                    type="submit",
                    cls="w-full px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-semibold rounded-lg transition-colors mb-3"
                ),
                method="post",
                action="/api/register",
            ),
            ft.Form(
                ft.Button(
                    "Cancel",
                    type="submit",
                    cls="w-full px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white font-semibold rounded-lg transition-colors"
                ),
                method="post",
                action="/api/register/cancel",
            ),
            cls="bg-gray-800 rounded-xl p-8 border border-gray-700 max-w-sm w-full mx-auto shadow-2xl"
        ),
        cls="container mx-auto px-4 py-16 flex justify-center"
    )
