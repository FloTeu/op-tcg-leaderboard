"""
Tests for OAuth auth routes (/login, /auth/{provider}, /logout).

Uses a minimal test app that only registers the auth routes to avoid importing
BigQuery/Firestore dependencies from main.py.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from starlette.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, RedirectResponse
from fasthtml.common import fast_app

from op_tcg.frontend.api.routes.auth import setup_auth_routes, _normalize_discord_user
from op_tcg.frontend.utils.csrf import get_csrf_token

TEST_SECRET = "test-secret-key"


def make_test_app():
    """Create a minimal ASGI app with only the auth routes registered."""
    app, rt = fast_app(pico=False)
    app.add_middleware(SessionMiddleware, secret_key=TEST_SECRET)
    setup_auth_routes(rt)

    @rt("/test/session")
    async def _session(request: Request):
        return JSONResponse(dict(request.session))

    @rt("/test/set-csrf")
    async def _set_csrf(request: Request):
        token = get_csrf_token(request.session)
        return JSONResponse({"csrf_token": token})

    return app


@pytest.fixture
def client():
    app = make_test_app()
    with TestClient(app, follow_redirects=False) as c:
        yield c


class TestLoginRoute:
    def test_login_provider_google_redirects(self, client):
        mock_response = RedirectResponse("https://accounts.google.com/o/oauth2/auth?state=test")
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth:
            mock_oauth.google.authorize_redirect = AsyncMock(return_value=mock_response)
            response = client.get("/login/google")

        assert response.status_code in (302, 307)
        assert "accounts.google.com" in response.headers["location"]
        mock_oauth.google.authorize_redirect.assert_called_once()

    def test_login_provider_discord_redirects(self, client):
        mock_response = RedirectResponse("https://discord.com/api/oauth2/authorize?state=test")
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth:
            mock_oauth.discord.authorize_redirect = AsyncMock(return_value=mock_response)
            response = client.get("/login/discord")

        assert response.status_code in (302, 307)
        assert "discord.com" in response.headers["location"]
        mock_oauth.discord.authorize_redirect.assert_called_once()

    def test_login_unknown_provider_redirects_to_login(self, client):
        response = client.get("/login/fakeprovider")
        assert response.status_code == 302
        assert response.headers["location"] == "/login"


class TestAuthCallbackRoute:
    def test_returning_user_logs_in_directly(self, client):
        mock_user = {
            "sub": "google-123",
            "name": "Test User",
            "email": "test@example.com",
            "picture": "https://example.com/pic.jpg",
        }
        expected_user = {**mock_user, "provider": "google"}
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value={"sub": "google-123"}), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login") as mock_update:
            mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": mock_user})

            response = client.get("/auth/google?code=valid_code&state=test_state")

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        mock_update.assert_called_once_with(expected_user)

        session = client.get("/test/session").json()
        assert session["user"]["sub"] == "google-123"
        assert session["user"]["provider"] == "google"
        assert session["flash"]["type"] == "success"
        assert "Welcome back" in session["flash"]["message"]

    def test_new_user_redirected_to_register(self, client):
        mock_user = {
            "sub": "google-new",
            "name": "New User",
            "email": "new@example.com",
        }
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value=None), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login") as mock_update:
            mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": mock_user})

            response = client.get("/auth/google?code=valid_code&state=test_state")

        assert response.status_code == 302
        assert response.headers["location"] == "/register"
        mock_update.assert_not_called()

        session = client.get("/test/session").json()
        assert "user" not in session
        assert session["pending_registration"]["sub"] == "google-new"
        assert session["pending_registration"]["provider"] == "google"

    def test_auth_access_denied_sets_error_flash(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth"):
            response = client.get("/auth/google?error=access_denied")

        assert response.status_code == 302
        assert response.headers["location"] == "/"

        session = client.get("/test/session").json()
        assert "user" not in session
        assert session["flash"]["type"] == "error"
        assert "cancelled" in session["flash"]["message"].lower()

    def test_auth_server_error_includes_description(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth"):
            response = client.get("/auth/google?error=server_error&error_description=Internal+error")

        assert response.status_code == 302
        assert response.headers["location"] == "/"

        session = client.get("/test/session").json()
        assert session["flash"]["type"] == "error"
        assert "Internal error" in session["flash"]["message"]

    def test_auth_unknown_error_falls_back_to_error_code(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth"):
            response = client.get("/auth/google?error=temporarily_unavailable")

        session = client.get("/test/session").json()
        assert session["flash"]["type"] == "error"
        assert "temporarily_unavailable" in session["flash"]["message"]

    def test_token_exchange_failure_sets_error_flash(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.update_user_login"):
            mock_oauth.google.authorize_access_token = AsyncMock(
                side_effect=Exception("Token exchange failed")
            )

            response = client.get("/auth/google?code=bad_code")

        assert response.status_code == 302
        assert response.headers["location"] == "/"

        session = client.get("/test/session").json()
        assert "user" not in session
        assert session["flash"]["type"] == "error"
        assert "try again" in session["flash"]["message"].lower()

    def test_missing_userinfo_sets_error_flash(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.update_user_login"):
            mock_oauth.google.authorize_access_token = AsyncMock(
                return_value={"access_token": "abc123"}  # no 'userinfo' key
            )

            response = client.get("/auth/google?code=test_code")

        assert response.status_code == 302

        session = client.get("/test/session").json()
        assert "user" not in session
        assert session["flash"]["type"] == "error"
        assert "account info" in session["flash"]["message"].lower()

    def test_firestore_error_is_non_blocking(self, client):
        """User should still be logged in even if the Firestore update fails."""
        mock_user = {"sub": "google-456", "name": "Test User", "email": "test@example.com"}
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value={"sub": "google-456"}), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login",
                      side_effect=Exception("Firestore unavailable")):
            mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": mock_user})

            response = client.get("/auth/google?code=test_code")

        assert response.status_code == 302

        session = client.get("/test/session").json()
        assert session["user"]["sub"] == "google-456"
        assert session["flash"]["type"] == "success"

    def test_unknown_provider_callback_redirects_home(self, client):
        response = client.get("/auth/fakeprovider?code=test")
        assert response.status_code == 302
        assert response.headers["location"] == "/"


class TestLogoutRoute:
    def test_logout_clears_user_from_session(self, client):
        mock_user = {"sub": "google-789", "name": "Test User", "email": "test@example.com"}
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value={"sub": "google-789"}), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login"):
            mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": mock_user})
            client.get("/auth/google?code=test_code")

        assert "user" in client.get("/test/session").json()

        response = client.get("/logout")

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        assert "user" not in client.get("/test/session").json()

    def test_logout_when_not_logged_in_still_redirects(self, client):
        response = client.get("/logout")

        assert response.status_code == 302
        assert response.headers["location"] == "/"


class TestRegistrationFlow:
    """Tests for the registration confirmation flow (new / re-registering users)."""

    PENDING_USER = {"sub": "google-new", "name": "New User", "email": "new@example.com", "provider": "google"}

    def _set_pending(self, client):
        """Seed pending_registration and CSRF token via the auth callback."""
        base_user = {k: v for k, v in self.PENDING_USER.items() if k != 'provider'}
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value=None), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login"):
            mock_oauth.google.authorize_access_token = AsyncMock(return_value={"userinfo": base_user})
            client.get("/auth/google?code=test_code")
        return client.get("/test/set-csrf").json()["csrf_token"]

    def test_confirm_registration_creates_user_and_logs_in(self, client):
        csrf = self._set_pending(client)
        with patch("op_tcg.frontend.api.routes.auth.update_user_login") as mock_create:
            response = client.post("/api/register", data={"csrf_token": csrf})

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        mock_create.assert_called_once_with(self.PENDING_USER)

        session = client.get("/test/session").json()
        assert session["user"]["sub"] == "google-new"
        assert "pending_registration" not in session
        assert session["flash"]["type"] == "success"
        assert "created" in session["flash"]["message"].lower()

    def test_confirm_registration_wrong_csrf_redirects_back(self, client):
        self._set_pending(client)
        with patch("op_tcg.frontend.api.routes.auth.update_user_login") as mock_create:
            response = client.post("/api/register", data={"csrf_token": "forged"})

        assert response.status_code == 302
        assert response.headers["location"] == "/register"
        mock_create.assert_not_called()

        session = client.get("/test/session").json()
        assert "user" not in session
        assert "pending_registration" in session

    def test_confirm_registration_without_pending_redirects_home(self, client):
        response = client.post("/api/register", data={"csrf_token": "any"})
        assert response.status_code == 302
        assert response.headers["location"] == "/"

    def test_cancel_registration_clears_pending_and_redirects_home(self, client):
        self._set_pending(client)
        assert "pending_registration" in client.get("/test/session").json()

        response = client.post("/api/register/cancel")

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        assert "pending_registration" not in client.get("/test/session").json()


class TestNormalizeDiscordUser:
    DISCORD_RAW = {
        "id": "987654321",
        "username": "pirate_king",
        "global_name": "Monkey D. Luffy",
        "email": "luffy@onepiece.com",
        "avatar": "abc123hash",
    }
    EXPECTED = {
        "sub": "discord_987654321",
        "name": "Monkey D. Luffy",
        "email": "luffy@onepiece.com",
        "picture": "https://cdn.discordapp.com/avatars/987654321/abc123hash.png",
        "provider": "discord",
    }

    def test_full_user(self):
        assert _normalize_discord_user(self.DISCORD_RAW) == self.EXPECTED

    def test_no_avatar(self):
        result = _normalize_discord_user({**self.DISCORD_RAW, "avatar": None})
        assert result["picture"] is None

    def test_no_global_name_falls_back_to_username(self):
        result = _normalize_discord_user({**self.DISCORD_RAW, "global_name": None})
        assert result["name"] == "pirate_king"


class TestDiscordAuthFlow:
    DISCORD_RAW = {
        "id": "987654321",
        "username": "pirate_king",
        "global_name": "Monkey D. Luffy",
        "email": "luffy@onepiece.com",
        "avatar": "abc123hash",
    }
    EXPECTED_USER = {
        "sub": "discord_987654321",
        "name": "Monkey D. Luffy",
        "email": "luffy@onepiece.com",
        "picture": "https://cdn.discordapp.com/avatars/987654321/abc123hash.png",
        "provider": "discord",
    }

    def _mock_discord_oauth(self, mock_oauth):
        mock_resp = MagicMock()
        mock_resp.json.return_value = self.DISCORD_RAW
        mock_resp.raise_for_status = MagicMock()
        mock_oauth.discord.authorize_access_token = AsyncMock(return_value={"access_token": "tok"})
        mock_oauth.discord.get = AsyncMock(return_value=mock_resp)

    def test_returning_discord_user_logs_in(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value={"sub": "discord_987654321"}), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login") as mock_update:
            self._mock_discord_oauth(mock_oauth)
            response = client.get("/auth/discord?code=valid_code&state=test_state")

        assert response.status_code == 302
        assert response.headers["location"] == "/"
        mock_update.assert_called_once_with(self.EXPECTED_USER)

        session = client.get("/test/session").json()
        assert session["user"]["sub"] == "discord_987654321"
        assert session["user"]["provider"] == "discord"

    def test_new_discord_user_goes_to_register(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth, \
                patch("op_tcg.frontend.api.routes.auth.get_user", return_value=None), \
                patch("op_tcg.frontend.api.routes.auth.update_user_login"):
            self._mock_discord_oauth(mock_oauth)
            response = client.get("/auth/discord?code=valid_code&state=test_state")

        assert response.status_code == 302
        assert response.headers["location"] == "/register"

        session = client.get("/test/session").json()
        assert session["pending_registration"]["sub"] == "discord_987654321"
        assert session["pending_registration"]["provider"] == "discord"

    def test_discord_userinfo_fetch_failure_sets_error_flash(self, client):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock(side_effect=Exception("HTTP 401"))

        with patch("op_tcg.frontend.api.routes.auth.oauth") as mock_oauth:
            mock_oauth.discord.authorize_access_token = AsyncMock(return_value={"access_token": "tok"})
            mock_oauth.discord.get = AsyncMock(return_value=mock_resp)

            response = client.get("/auth/discord?code=test_code")

        assert response.status_code == 302
        session = client.get("/test/session").json()
        assert session["flash"]["type"] == "error"
        assert "account info" in session["flash"]["message"].lower()

    def test_discord_access_denied_sets_error_flash(self, client):
        with patch("op_tcg.frontend.api.routes.auth.oauth"):
            response = client.get("/auth/discord?error=access_denied")

        assert response.status_code == 302
        session = client.get("/test/session").json()
        assert session["flash"]["type"] == "error"
        assert "cancelled" in session["flash"]["message"].lower()
