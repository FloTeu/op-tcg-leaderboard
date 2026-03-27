from starlette.requests import Request
from starlette.responses import RedirectResponse
from op_tcg.backend.auth import oauth
from op_tcg.backend.db import update_user_login, get_user
from op_tcg.frontend.utils.csrf import validate_csrf_token
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
        # Handle errors returned directly by the OAuth provider (e.g. user denied access)
        error = request.query_params.get("error")
        if error:
            error_description = request.query_params.get("error_description", "")
            if error == "access_denied":
                msg = "Login was cancelled."
            else:
                msg = f"Login failed: {error_description or error}"
            logger.warning(f"OAuth provider error: {error} – {error_description}")
            request.session['flash'] = {"message": msg, "type": "error"}
            return RedirectResponse(url='/', status_code=302)

        try:
            token = await oauth.google.authorize_access_token(request)
        except Exception as e:
            logger.error(f"Error authorizing access token: {e}")
            request.session['flash'] = {"message": "Login failed. Please try again.", "type": "error"}
            return RedirectResponse(url='/', status_code=302)

        user = token.get('userinfo')
        if not user:
            logger.error("No userinfo in token response")
            request.session['flash'] = {"message": "Login failed: could not retrieve account info.", "type": "error"}
            return RedirectResponse(url='/', status_code=302)

        # New users must confirm registration before being logged in
        try:
            existing = get_user(user['sub'])
        except Exception as e:
            logger.error(f"Error checking user existence, skipping registration gate: {e}")
            existing = True  # fail safe: don't block login if Firestore is unavailable

        if not existing:
            request.session['pending_registration'] = dict(user)
            return RedirectResponse(url='/register', status_code=302)

        # Returning user — update last_login (non-blocking)
        try:
            update_user_login(user)
        except Exception as e:
            logger.error(f"Error updating user in Firestore: {e}")

        request.session['user'] = user
        request.session['flash'] = {"message": f"Welcome back, {user.get('name', 'there')}!", "type": "success"}
        return RedirectResponse(url='/', status_code=302)

    @rt("/api/register", methods=["POST"])
    async def confirm_registration(request: Request):
        pending = request.session.get('pending_registration')
        if not pending:
            return RedirectResponse(url='/', status_code=302)

        form = await request.form()
        if not validate_csrf_token(request.session, form.get("csrf_token")):
            request.session['flash'] = {"message": "Invalid request. Please try again.", "type": "error"}
            return RedirectResponse(url='/register', status_code=302)

        try:
            update_user_login(pending)
        except Exception as e:
            logger.error(f"Error creating user in Firestore: {e}")

        request.session.pop('pending_registration', None)
        request.session['user'] = pending
        request.session['flash'] = {"message": f"Welcome, {pending.get('name', 'there')}! Your account has been created.", "type": "success"}
        return RedirectResponse(url='/', status_code=302)

    @rt("/api/register/cancel", methods=["POST"])
    async def cancel_registration(request: Request):
        request.session.pop('pending_registration', None)
        return RedirectResponse(url='/', status_code=302)

    @rt("/logout", name="logout")
    async def logout(request: Request):
        request.session.pop('user', None)
        return RedirectResponse(url='/', status_code=302)


