from starlette.requests import Request
from starlette.responses import RedirectResponse
from op_tcg.backend.auth import oauth
from op_tcg.backend.db import update_user_login
import logging

logger = logging.getLogger(__name__)

def setup_auth_routes(rt):

    @rt("/login", name="login")
    async def login(request: Request):
        # request.url_for uses the server's bind address if not proxied correctly
        redirect_uri = str(request.url_for('auth'))

        # Replace 0.0.0.0 with localhost for local development
        if "0.0.0.0" in redirect_uri:
            redirect_uri = redirect_uri.replace("0.0.0.0", "localhost")

        return await oauth.google.authorize_redirect(request, redirect_uri)

    @rt("/auth", name="auth")
    async def auth(request: Request):
        try:
            token = await oauth.google.authorize_access_token(request)
        except Exception as e:
            logger.error(f"Error authorizing access token: {e}")
            return RedirectResponse(url='/')

        user = token.get('userinfo')
        if user:
            # Update user in Firestore
            try:
                update_user_login(user)
            except Exception as e:
                logger.error(f"Error updating user in Firestore: {e}")

            request.session['user'] = user
        return RedirectResponse(url='/')

    @rt("/logout", name="logout")
    async def logout(request: Request):
        request.session.pop('user', None)
        return RedirectResponse(url='/')


