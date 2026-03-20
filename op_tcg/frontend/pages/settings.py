from fasthtml import ft
from op_tcg.backend.db import get_user_settings
from op_tcg.backend.models.input import MetaFormatRegion
from op_tcg.backend.models.cards import CardCurrency


_RADIO_ACTIVE = "bg-blue-600 border-blue-500 text-white"
_RADIO_INACTIVE = "border-gray-600 text-gray-400 hover:border-gray-400 hover:text-white"
_RADIO_BASE = "px-4 py-2 rounded-lg border cursor-pointer text-sm font-medium transition-colors "
_RADIO_ONCHANGE = (
    "var g=this.closest('.radio-group');"
    "g.querySelectorAll('span[data-radio]').forEach(function(s){"
    "s.className='" + _RADIO_BASE + _RADIO_INACTIVE + "'});"
    "this.nextElementSibling.className='" + _RADIO_BASE + _RADIO_ACTIVE + "';"
)


def _radio(name: str, value: str, label: str, checked: bool) -> ft.Label:
    span_cls = _RADIO_BASE + (_RADIO_ACTIVE if checked else _RADIO_INACTIVE)
    return ft.Label(
        ft.Input(
            type="radio",
            name=name,
            value=value,
            checked=checked,
            cls="sr-only",
            onchange=_RADIO_ONCHANGE,
        ),
        ft.Span(label, cls=span_cls, data_radio="1"),
        cls="inline-flex"
    )


def settings_content(user=None):
    if not user:
        return ft.Div(
            ft.H1("Access Denied", cls="text-2xl font-bold text-white mb-4"),
            ft.P("Please login to manage your settings.", cls="text-gray-400"),
            ft.A("Login", href="/login",
                 cls="mt-4 inline-block px-5 py-2 bg-blue-600 hover:bg-blue-700 text-white rounded-lg text-sm font-medium transition-colors"),
            cls="container mx-auto px-4 py-8"
        )

    user_settings = get_user_settings(user['sub'])
    current_currency = user_settings.get("currency", CardCurrency.EURO)
    current_region = user_settings.get("region", MetaFormatRegion.ALL)

    return ft.Div(
        ft.H1("Settings", cls="text-2xl font-bold text-white mb-8"),

        ft.Form(
            # ── Currency ──────────────────────────────────────────────
            ft.Div(
                ft.H2("Default Currency", cls="text-lg font-semibold text-white mb-1"),
                ft.P("Used on price pages and your watchlist.", cls="text-sm text-gray-400 mb-4"),
                ft.Div(
                    _radio("currency", CardCurrency.EURO, "€ EUR", current_currency == CardCurrency.EURO),
                    _radio("currency", CardCurrency.US_DOLLAR, "$ USD", current_currency == CardCurrency.US_DOLLAR),
                    cls="flex gap-3 radio-group"
                ),
                cls="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-4"
            ),

            # ── Region / Meta ──────────────────────────────────────────
            ft.Div(
                ft.H2("Default Region", cls="text-lg font-semibold text-white mb-1"),
                ft.P("Pre-selects the meta region filter across leaderboard pages.", cls="text-sm text-gray-400 mb-4"),
                ft.Div(
                    _radio("region", MetaFormatRegion.ALL, "All", current_region == MetaFormatRegion.ALL),
                    _radio("region", MetaFormatRegion.WEST, "West", current_region == MetaFormatRegion.WEST),
                    _radio("region", MetaFormatRegion.ASIA, "Asia", current_region == MetaFormatRegion.ASIA),
                    cls="flex gap-3 radio-group"
                ),
                cls="bg-gray-800 rounded-lg p-6 border border-gray-700 mb-6"
            ),

            # ── Save button + inline feedback ─────────────────────────
            ft.Div(
                ft.Button(
                    ft.I(cls="fas fa-save mr-2"),
                    "Save Settings",
                    type="submit",
                    cls="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-semibold rounded-lg transition-colors"
                ),
                ft.Span(id="settings-save-feedback", cls="ml-4"),
                cls="flex items-center"
            ),

            hx_post="/api/settings",
            hx_target="#settings-save-feedback",
            hx_swap="outerHTML",
        ),

        # ── Danger zone ───────────────────────────────────────────────
        ft.Div(
            ft.H2("Danger Zone", cls="text-lg font-semibold text-red-400 mb-1"),
            ft.P("Permanently deletes your account, watchlist, and all stored data. This cannot be undone.",
                 cls="text-sm text-gray-400 mb-4"),
            ft.Button(
                ft.I(cls="fas fa-trash-alt mr-2"),
                "Delete My Account",
                type="button",
                onclick="document.getElementById('delete-account-modal').classList.remove('hidden')",
                cls="px-5 py-2 bg-red-700 hover:bg-red-600 text-white text-sm font-semibold rounded-lg transition-colors border border-red-600"
            ),
            cls="bg-gray-800 rounded-lg p-6 border border-red-900 mt-8"
        ),

        # ── Delete confirmation modal ─────────────────────────────────
        ft.Div(
            ft.Div(
                ft.Div(
                    ft.I(cls="fas fa-exclamation-triangle text-red-400 text-3xl mb-4"),
                    ft.H3("Delete Account?", cls="text-xl font-bold text-white mb-2"),
                    ft.P("All your data — including your watchlist — will be permanently removed.",
                         cls="text-gray-400 text-sm mb-6"),
                    ft.Div(
                        ft.Button(
                            "Yes, delete my account",
                            type="button",
                            hx_post="/api/delete-account",
                            cls="px-5 py-2 bg-red-600 hover:bg-red-700 text-white text-sm font-semibold rounded-lg transition-colors"
                        ),
                        ft.Button(
                            "Cancel",
                            type="button",
                            onclick="document.getElementById('delete-account-modal').classList.add('hidden')",
                            cls="px-5 py-2 bg-gray-700 hover:bg-gray-600 text-white text-sm font-semibold rounded-lg transition-colors"
                        ),
                        cls="flex gap-3 justify-center"
                    ),
                    cls="text-center"
                ),
                cls="bg-gray-800 rounded-xl p-8 border border-gray-700 max-w-md w-full mx-4 shadow-2xl"
            ),
            id="delete-account-modal",
            cls="hidden fixed inset-0 bg-black bg-opacity-70 flex items-center justify-center z-50",
            onclick="if(event.target===this)this.classList.add('hidden')"
        ),

        cls="container mx-auto px-4 py-8 max-w-2xl"
    )
