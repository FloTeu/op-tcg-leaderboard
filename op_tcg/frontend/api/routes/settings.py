from fasthtml import ft
from starlette.requests import Request
from starlette.responses import RedirectResponse, Response
from op_tcg.backend.db import get_user_settings, update_user_settings, delete_user
from op_tcg.backend.models.cards import CardCurrency
from op_tcg.backend.models.input import MetaFormatRegion


def setup_settings_routes(rt):

    @rt("/api/settings", methods=["POST"])
    async def save_settings(request: Request):
        user = request.session.get('user')
        if not user:
            return ft.Div("Unauthorized", cls="text-red-400")

        form = await request.form()
        settings = {
            "currency": CardCurrency(form.get("currency", CardCurrency.EURO)).value,
            "region": MetaFormatRegion(form.get("region", MetaFormatRegion.ALL)).value,
        }
        update_user_settings(user['sub'], settings)

        return ft.Div(
            ft.I(cls="fas fa-check-circle mr-2 text-green-400"),
            "Settings saved",
            cls="flex items-center text-green-400 text-sm font-medium",
            id="settings-save-feedback",
        )

    @rt("/api/delete-account", methods=["POST"])
    async def delete_account(request: Request):
        if not request.headers.get("HX-Request"):
            return RedirectResponse(url="/", status_code=303)
        user = request.session.get('user')
        if not user:
            return RedirectResponse(url="/", status_code=303)

        delete_user(user['sub'])
        request.session.pop('user', None)
        return Response(status_code=200, headers={"HX-Redirect": "/"})
