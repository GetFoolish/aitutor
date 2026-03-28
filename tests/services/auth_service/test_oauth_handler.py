import pytest

from services.AuthService.oauth_handler import GoogleOAuthHandler
from services.AuthService import oauth_handler


class FakeOAuthClient:
    def __init__(self, *args, **kwargs):
        self.closed = False

    def create_authorization_url(self, url, scope):
        return ("https://accounts.google.com/o/oauth2/v2/auth?state=state-123", "state-123")

    async def fetch_token(self, url, code, authorization_response):
        self.fetch_args = (url, code, authorization_response)

    async def get(self, url):
        class Response:
            def json(self):
                return {
                    "id": "google-user",
                    "email": "student@example.com",
                    "name": "Student",
                    "picture": "https://example.com/avatar.png",
                    "verified_email": True,
                }

        return Response()

    async def aclose(self):
        self.closed = True


def test_get_authorization_url_requires_credentials(monkeypatch):
    handler = GoogleOAuthHandler("https://example.com/callback")
    monkeypatch.setattr(oauth_handler, "GOOGLE_CLIENT_ID", None)
    monkeypatch.setattr(oauth_handler, "GOOGLE_CLIENT_SECRET", None)

    with pytest.raises(ValueError, match="GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET must be set"):
        handler.get_authorization_url()


def test_get_authorization_url_and_user_info(monkeypatch):
    handler = GoogleOAuthHandler("https://example.com/callback")
    monkeypatch.setattr(oauth_handler, "GOOGLE_CLIENT_ID", "client-id")
    monkeypatch.setattr(oauth_handler, "GOOGLE_CLIENT_SECRET", "client-secret")
    monkeypatch.setattr(handler, "_build_client", lambda state=None: FakeOAuthClient())

    url, state = handler.get_authorization_url()

    assert "state=state-123" in url
    assert state == "state-123"

    user_info = __import__("asyncio").run(handler.get_user_info("code-123", "state-123", "https://example.com/callback"))

    assert user_info == {
        "id": "google-user",
        "email": "student@example.com",
        "name": "Student",
        "picture": "https://example.com/avatar.png",
        "verified_email": True,
    }


def test_get_user_info_returns_none_on_failure(monkeypatch):
    class FailingClient(FakeOAuthClient):
        async def fetch_token(self, url, code, authorization_response):
            raise RuntimeError("oauth failed")

    handler = GoogleOAuthHandler("https://example.com/callback")
    monkeypatch.setattr(handler, "_build_client", lambda state=None: FailingClient())

    assert __import__("asyncio").run(handler.get_user_info("code-123", "state-123", "https://example.com/callback")) is None
