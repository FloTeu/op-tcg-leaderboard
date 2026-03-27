"""
Tests for settings API routes (/api/settings, /api/delete-account).
"""
import pytest
from unittest.mock import MagicMock, patch
from starlette.testclient import TestClient
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from fasthtml.common import fast_app

from op_tcg.frontend.api.routes.settings import setup_settings_routes
from op_tcg.frontend.utils.csrf import get_csrf_token

TEST_SECRET = "test-secret-key"
MOCK_USER = {"sub": "google-123", "name": "Test User", "email": "test@example.com"}


def make_test_app():
    app, rt = fast_app(pico=False)
    app.add_middleware(SessionMiddleware, secret_key=TEST_SECRET)
    setup_settings_routes(rt)

    @rt("/test/set-user")
    async def _set_user(request: Request):
        request.session['user'] = MOCK_USER
        get_csrf_token(request.session)
        return JSONResponse({"csrf_token": request.session['csrf_token']})

    @rt("/test/session")
    async def _session(request: Request):
        return JSONResponse(dict(request.session))

    return app


@pytest.fixture
def client():
    app = make_test_app()
    with TestClient(app, follow_redirects=False) as c:
        yield c


@pytest.fixture
def authed_client(client):
    data = client.get("/test/set-user").json()
    client._csrf_token = data["csrf_token"]
    return client


class TestSaveSettings:
    def test_valid_csrf_saves_settings(self, authed_client):
        with patch("op_tcg.frontend.api.routes.settings.update_user_settings") as mock_update, \
                patch("op_tcg.frontend.api.routes.settings.get_user_settings", return_value={}):
            response = authed_client.post(
                "/api/settings",
                data={"currency": "eur", "region": "all", "csrf_token": authed_client._csrf_token},
                headers={"HX-Request": "true"},
            )
        assert response.status_code == 200
        mock_update.assert_called_once()

    def test_missing_csrf_rejected(self, authed_client):
        with patch("op_tcg.frontend.api.routes.settings.update_user_settings") as mock_update, \
                patch("op_tcg.frontend.api.routes.settings.get_user_settings", return_value={}):
            response = authed_client.post(
                "/api/settings",
                data={"currency": "eur", "region": "all"},
                headers={"HX-Request": "true"},
            )
        assert response.status_code == 200
        assert "Invalid request" in response.text
        mock_update.assert_not_called()

    def test_wrong_csrf_rejected(self, authed_client):
        with patch("op_tcg.frontend.api.routes.settings.update_user_settings") as mock_update, \
                patch("op_tcg.frontend.api.routes.settings.get_user_settings", return_value={}):
            response = authed_client.post(
                "/api/settings",
                data={"currency": "eur", "region": "all", "csrf_token": "wrong-token"},
                headers={"HX-Request": "true"},
            )
        assert response.status_code == 200
        assert "Invalid request" in response.text
        mock_update.assert_not_called()

    def test_unauthenticated_rejected(self, client):
        response = client.post(
            "/api/settings",
            data={"currency": "eur", "csrf_token": "any"},
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 200
        assert "Unauthorized" in response.text


class TestDeleteAccount:
    def test_valid_csrf_deletes_account(self, authed_client):
        with patch("op_tcg.frontend.api.routes.settings.delete_user") as mock_delete:
            response = authed_client.post(
                "/api/delete-account",
                data={"csrf_token": authed_client._csrf_token},
                headers={"HX-Request": "true"},
            )
        assert response.status_code == 200
        mock_delete.assert_called_once_with(MOCK_USER["sub"])
        assert "user" not in authed_client.get("/test/session").json()

    def test_missing_csrf_returns_403(self, authed_client):
        with patch("op_tcg.frontend.api.routes.settings.delete_user") as mock_delete:
            response = authed_client.post(
                "/api/delete-account",
                data={},
                headers={"HX-Request": "true"},
            )
        assert response.status_code == 403
        mock_delete.assert_not_called()

    def test_wrong_csrf_returns_403(self, authed_client):
        with patch("op_tcg.frontend.api.routes.settings.delete_user") as mock_delete:
            response = authed_client.post(
                "/api/delete-account",
                data={"csrf_token": "forged-token"},
                headers={"HX-Request": "true"},
            )
        assert response.status_code == 403
        mock_delete.assert_not_called()

    def test_non_htmx_request_redirects(self, authed_client):
        response = authed_client.post(
            "/api/delete-account",
            data={"csrf_token": authed_client._csrf_token},
        )
        assert response.status_code == 303

    def test_unauthenticated_redirects(self, client):
        response = client.post(
            "/api/delete-account",
            data={"csrf_token": "any"},
            headers={"HX-Request": "true"},
        )
        assert response.status_code == 303
