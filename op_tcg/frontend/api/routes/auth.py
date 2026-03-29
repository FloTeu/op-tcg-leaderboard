from starlette.requests import Request
from starlette.responses import RedirectResponse
from op_tcg.backend.auth import oauth
from op_tcg.backend.db import update_user_login, get_user
from op_tcg.frontend.utils.csrf import validate_csrf_token
import logging

logger = logging.getLogger(__name__)

VALID_PROVIDERS = ('google', 'discord')


def _normalize_discord_user(discord_user: dict) -> dict:
    user_id = discord_user.get('id', '')
    avatar_hash = discord_user.get('avatar')
    picture = f"https://cdn.discordapp.com/avatars/{user_id}/{avatar_hash}.png" if avatar_hash else None
    return {
        'sub': f'discord_{user_id}',
        'name': discord_user.get('global_name') or discord_user.get('username', ''),
        'email': discord_user.get('email', ''),
        'picture': picture,
        'provider': 'discord',
    }


def setup_auth_routes(rt):

    @rt("/login", name="login")
    async def login_page(request: Request):
        from op_tcg.frontend.components.layout import layout
        from op_tcg.frontend.pages.login import login_provider_select_content
        flash = request.session.pop('flash', None)
        user = request.session.get('user')
        return layout(login_provider_select_content(), current_path="/login", user=user, flash=flash)

    @rt("/login/{provider}", name="login_provider")
    async def login_provider(request: Request, provider: str):
        if provider not in VALID_PROVIDERS:
            request.session['flash'] = {"message": "Unknown login provider.", "type": "error"}
            return RedirectResponse(url='/login', status_code=302)

        redirect_uri = str(request.url_for('auth_callback', provider=provider))
        if "0.0.0.0" in redirect_uri:
            redirect_uri = redirect_uri.replace("0.0.0.0", "localhost")

        client = getattr(oauth, provider)
        return await client.authorize_redirect(request, redirect_uri)

    @rt("/auth/{provider}", name="auth_callback")
    async def auth_callback(request: Request, provider: str):
        if provider not in VALID_PROVIDERS:
            request.session['flash'] = {"message": "Unknown login provider.", "type": "error"}
            return RedirectResponse(url='/', status_code=302)

        error = request.query_params.get("error")
        if error:
            error_description = request.query_params.get("error_description", "")
            if error == "access_denied":
                msg = "Login was cancelled."
            else:
                msg = f"Login failed: {error_description or error}"
            logger.warning(f"OAuth provider error [{provider}]: {error} – {error_description}")
            request.session['flash'] = {"message": msg, "type": "error"}
            return RedirectResponse(url='/', status_code=302)

        client = getattr(oauth, provider)

        try:
            token = await client.authorize_access_token(request)
        except Exception as e:
            logger.error(f"Error authorizing access token [{provider}]: {e}")
            request.session['flash'] = {"message": "Login failed. Please try again.", "type": "error"}
            return RedirectResponse(url='/', status_code=302)

        if provider == 'google':
            raw_user = token.get('userinfo')
            if not raw_user:
                logger.error("No userinfo in Google token response")
                request.session['flash'] = {"message": "Login failed: could not retrieve account info.", "type": "error"}
                return RedirectResponse(url='/', status_code=302)
            user = dict(raw_user)
            user['provider'] = 'google'
        else:  # discord
            try:
                resp = await client.get('users/@me', token=token)
                resp.raise_for_status()
                user = _normalize_discord_user(resp.json())
            except Exception as e:
                logger.error(f"Error fetching Discord userinfo: {e}")
                request.session['flash'] = {"message": "Login failed: could not retrieve account info.", "type": "error"}
                return RedirectResponse(url='/', status_code=302)

        try:
            existing = get_user(user['sub'])
        except Exception as e:
            logger.error(f"Error checking user existence, skipping registration gate: {e}")
            existing = True

        if not existing:
            request.session['pending_registration'] = user
            return RedirectResponse(url='/register', status_code=302)

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
