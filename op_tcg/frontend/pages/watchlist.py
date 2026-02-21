from fasthtml import ft
from op_tcg.backend.db import get_watchlist

def watchlist_page(request):
    user = request.session.get('user')
    if not user:
         return ft.Div(
             ft.H1("Access Denied", cls="text-2xl font-bold text-white mb-4"),
             ft.P("Please login to view your watchlist.", cls="text-gray-400"),
             cls="container mx-auto px-4 py-8"
         )

    user_id = user.get('sub')
    watchlist = get_watchlist(user_id)

    if not watchlist:
        return ft.Div(
            ft.H1("My Watchlist", cls="text-2xl font-bold text-white mb-4"),
            ft.P("Your watchlist is currently empty.", cls="text-gray-400"),
            cls="container mx-auto px-4 py-8"
        )

    # Simple list display
    # We will refine UI future as requested
    items = []
    for item in watchlist:
        items.append(
            ft.Div(
                ft.H3(f"{item.get('card_id')} - {item.get('card_version')} ({item.get('language')})", cls="text-white font-medium"),
                cls="bg-gray-800 p-4 rounded-lg shadow mb-2"
            )
        )

    return ft.Div(
        ft.H1("My Watchlist", cls="text-2xl font-bold text-white mb-4"),
        ft.Div(
            *items,
            cls="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"
        ),
        cls="container mx-auto px-4 py-8"
    )

