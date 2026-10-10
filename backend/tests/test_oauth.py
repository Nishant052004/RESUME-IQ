"""Module 8 tests — Google/GitHub OAuth authorization-code flow.

Provider network calls (token exchange + profile fetch) are monkeypatched, so
these tests run fully offline while exercising the real endpoints, state
signing, origin allow-listing, user upsert and error paths.
"""
import pytest

from app.auth import oauth
from app.config import settings

PROVIDER_PROFILE = {"email": "jane.doe@gmail.com", "name": "Jane Doe", "avatar": "https://avatars/p.png"}


@pytest.fixture
def google_configured(monkeypatch):
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_ID", "test-google-id", raising=False)
    monkeypatch.setattr(settings, "GOOGLE_CLIENT_SECRET", "test-google-secret", raising=False)


async def _exchange_ok(provider, code, redirect):
    assert code == "good-code"
    return "provider-access-token"


async def _profile_ok(provider, access_token):
    return dict(PROVIDER_PROFILE)


def test_oauth_status_reflects_configuration(client, google_configured):
    status = client.get("/api/auth/oauth/status").json()
    assert status["google"] is True
    assert status["github"] is False


def test_unconfigured_provider_redirects_to_login_hint(client):
    response = client.get("/api/auth/oauth/google", follow_redirects=False)
    assert response.status_code == 307
    assert "oauth_error=not_configured" in response.headers["location"]
    assert "provider=google" in response.headers["location"]


def test_unknown_provider_is_404(client):
    assert client.get("/api/auth/oauth/microsoft", follow_redirects=False).status_code == 404


def test_google_authorize_redirect_when_configured(client, google_configured):
    response = client.get("/api/auth/oauth/google?origin=http://testserver", follow_redirects=False)
    assert response.status_code == 307
    location = response.headers["location"]
    assert location.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=test-google-id" in location
    assert "redirect_uri=http" in location and "callback" in location
    assert "state=" in location


def test_github_authorize_redirect(client, monkeypatch):
    monkeypatch.setattr(settings, "GITHUB_CLIENT_ID", "test-gh-id", raising=False)
    monkeypatch.setattr(settings, "GITHUB_CLIENT_SECRET", "test-gh-secret", raising=False)
    response = client.get("/api/auth/oauth/github?origin=http://testserver", follow_redirects=False)
    assert response.status_code == 307
    assert response.headers["location"].startswith("https://github.com/login/oauth/authorize?")


def test_authorize_rejects_disallowed_origin(client, google_configured):
    """An attacker-supplied origin must never be embedded in the state: the
    endpoint silently falls back to the API's own origin."""
    response = client.get("/api/auth/oauth/google?origin=https://evil.example.com", follow_redirects=False)
    location = response.headers["location"]
    state = location.split("state=")[1].split("&")[0]
    embedded = oauth.verify_state(state, "http://testserver")
    assert embedded == "http://testserver"
    assert embedded != "https://evil.example.com"


def test_callback_full_flow_creates_user_and_issues_jwt(client, google_configured, monkeypatch):
    monkeypatch.setattr(oauth, "exchange_code", _exchange_ok)
    monkeypatch.setattr(oauth, "fetch_profile", _profile_ok)
    state = oauth.make_state("http://testserver")
    response = client.get(
        f"/api/auth/oauth/google/callback?code=good-code&state={state}", follow_redirects=False
    )
    assert response.status_code == 302
    location = response.headers["location"]
    assert location.startswith("http://testserver/oauth/callback?token=")
    token = location.split("token=")[1]

    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["email"] == "jane.doe@gmail.com"
    assert me["full_name"] == "Jane Doe"
    assert me["avatar_url"] == "https://avatars/p.png", "OAuth profile picture must be stored and returned"


def _profile_with(email):
    async def _fetch(provider, access_token):
        return {"email": email, "name": "Linked User", "avatar": ""}

    return _fetch


def test_callback_links_existing_account_by_email(client, google_configured, monkeypatch):
    registered = client.post(
        "/api/auth/register",
        json={"email": "jane.local@gmail.com", "password": "secret123", "full_name": "Jane Local"},
    )
    assert registered.status_code == 201, registered.text
    local_id = registered.json()["id"]
    monkeypatch.setattr(oauth, "exchange_code", _exchange_ok)
    monkeypatch.setattr(oauth, "fetch_profile", _profile_with("jane.local@gmail.com"))
    state = oauth.make_state("http://testserver")
    response = client.get(
        f"/api/auth/oauth/google/callback?code=good-code&state={state}", follow_redirects=False
    )
    token = response.headers["location"].split("token=")[1]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()
    assert me["id"] == local_id, "OAuth must sign into the existing account, not duplicate it"


def test_oauth_account_cannot_password_login(client, google_configured, monkeypatch):
    monkeypatch.setattr(oauth, "exchange_code", _exchange_ok)
    monkeypatch.setattr(oauth, "fetch_profile", _profile_ok)
    state = oauth.make_state("http://testserver")
    response = client.get(
        f"/api/auth/oauth/google/callback?code=good-code&state={state}", follow_redirects=False
    )
    token = response.headers["location"].split("token=")[1]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"}).json()

    assert client.post("/api/auth/login", json={"email": me["email"], "password": "anything123"}).status_code == 401


def test_callback_rejects_tampered_or_stale_state(client, google_configured):
    response = client.get(
        "/api/auth/oauth/google/callback?code=good-code&state=not-a-jwt", follow_redirects=False
    )
    assert "oauth_error=invalid_state" in response.headers["location"]

    evil_state = oauth.make_state("https://evil.example.com")
    response = client.get(
        f"/api/auth/oauth/google/callback?code=good-code&state={evil_state}", follow_redirects=False
    )
    assert "oauth_error=invalid_state" in response.headers["location"]


def test_callback_requires_code(client, google_configured):
    state = oauth.make_state("http://testserver")
    response = client.get(f"/api/auth/oauth/google/callback?state={state}", follow_redirects=False)
    assert "oauth_error=missing_code" in response.headers["location"]


def test_callback_maps_provider_failure_to_error_redirect(client, google_configured, monkeypatch):
    def boom(provider, code, redirect):
        raise RuntimeError("exchange down")

    monkeypatch.setattr(oauth, "exchange_code", boom)
    state = oauth.make_state("http://testserver")
    response = client.get(
        f"/api/auth/oauth/google/callback?code=good-code&state={state}", follow_redirects=False
    )
    assert "oauth_error=provider_error" in response.headers["location"]


async def _profile_no_email(provider, access_token):
    return {"email": None, "name": "No Email", "avatar": ""}


def test_callback_without_email_redirects_with_reason(client, google_configured, monkeypatch):
    monkeypatch.setattr(oauth, "exchange_code", _exchange_ok)
    monkeypatch.setattr(oauth, "fetch_profile", _profile_no_email)
    state = oauth.make_state("http://testserver")
    response = client.get(
        f"/api/auth/oauth/google/callback?code=good-code&state={state}", follow_redirects=False
    )
    assert "oauth_error=no_email" in response.headers["location"]


def test_github_primary_email_picked_from_emails_list():
    """GitHub hides the private email on /user — the picker must choose the verified primary."""
    profile = {"email": None, "name": "GH User", "avatar": "x"}
    resolved = oauth.pick_primary_email(profile, [
        {"email": "secondary@example.com", "primary": False, "verified": True},
        {"email": "primary@example.com", "primary": True, "verified": True},
    ])
    assert resolved["email"] == "primary@example.com"

    # Keeps an existing email untouched and handles an empty list.
    assert oauth.pick_primary_email({"email": "keep@x.com"}, [])[ "email" ] == "keep@x.com"
    assert oauth.pick_primary_email({"email": None}, [])["email"] is None
