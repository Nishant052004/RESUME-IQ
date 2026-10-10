"""OAuth 2.0 authorization-code sign-in for Google & GitHub (Module 8).

Flow:
1. `GET /api/auth/oauth/{provider}?origin=<spa-origin>` → 307 to the provider's
   consent screen. The SPA origin rides inside a signed, short-lived `state`
   (a JWT) so the callback can only redirect to allow-listed origins.
2. Provider redirects to `GET /api/auth/oauth/{provider}/callback?code&state`.
3. We exchange the code for an access token, fetch the profile, upsert the
   user by email, and 302 back to `<origin>/oauth/callback?token=<our JWT>`.

Without client credentials configured the start endpoint redirects back to the
login page with `?oauth_error=not_configured` instead of failing — the UI
shows a setup hint.
"""
import secrets
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
import jwt

from ..config import settings

PROVIDERS: dict[str, dict] = {
    "google": {
        "authorize_url": "https://accounts.google.com/o/oauth2/v2/auth",
        "token_url": "https://oauth2.googleapis.com/token",
        "userinfo_url": "https://www.googleapis.com/oauth2/v3/userinfo",
        "scope": "openid email profile",
        "id": "GOOGLE_CLIENT_ID",
        "secret": "GOOGLE_CLIENT_SECRET",
        "extra_auth_params": {"prompt": "select_account"},
    },
    "github": {
        "authorize_url": "https://github.com/login/oauth/authorize",
        "token_url": "https://github.com/login/oauth/access_token",
        "userinfo_url": "https://api.github.com/user",
        "scope": "read:user user:email",
        "id": "GITHUB_CLIENT_ID",
        "secret": "GITHUB_CLIENT_SECRET",
        "extra_auth_params": {},
    },
}


def provider_credentials(provider: str) -> tuple[str, str]:
    client_id = getattr(settings, PROVIDERS[provider]["id"], "")
    client_secret = getattr(settings, PROVIDERS[provider]["secret"], "")
    return client_id, client_secret


def is_configured(provider: str) -> bool:
    client_id, client_secret = provider_credentials(provider)
    return bool(client_id and client_secret)


def redirect_uri(request_base_url: str, provider: str) -> str:
    return f"{request_base_url.rstrip('/')}/api/auth/oauth/{provider}/callback"


def allowed_origins(request_base_url: str) -> list[str]:
    origins = {o.strip().rstrip("/") for o in settings.CORS_ORIGINS.split(",") if o.strip()}
    origins.add(request_base_url.rstrip("/"))  # single-server mode: SPA served by the API
    return sorted(origins)


def make_state(origin: str) -> str:
    payload = {
        "origin": origin,
        "nonce": secrets.token_urlsafe(8),
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.OAUTH_STATE_TTL_MINUTES),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def verify_state(state: str, request_base_url: str) -> str | None:
    """Return the state's origin if valid AND allow-listed, else None."""
    try:
        payload = jwt.decode(state, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        origin = str(payload["origin"]).rstrip("/")
    except (jwt.PyJWTError, KeyError):
        return None
    return origin if origin in allowed_origins(request_base_url) else None


async def exchange_code(provider: str, code: str, redirect: str) -> str:
    """Trade the authorization code for an access token."""
    client_id, client_secret = provider_credentials(provider)
    spec = PROVIDERS[provider]
    headers = {"Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.post(
            spec["token_url"],
            data={
                "code": code,
                "client_id": client_id,
                "client_secret": client_secret,
                "redirect_uri": redirect,
                "grant_type": "authorization_code",
            },
            headers=headers,
        )
    if response.status_code != 200:
        raise RuntimeError(f"Token exchange failed ({response.status_code}).")
    token = response.json().get("access_token")
    if not token:
        raise RuntimeError("Provider did not return an access token.")
    return token


def pick_primary_email(profile: dict, emails: list) -> dict:
    """GitHub hides the private email on /user; choose the verified primary."""
    if not profile.get("email") and isinstance(emails, list):
        primary = next((e for e in emails if e.get("primary")), None)
        if primary:
            profile["email"] = primary.get("email")
    return profile


async def fetch_profile(provider: str, access_token: str) -> dict:
    """Fetch {email, name, avatar} from the provider."""
    spec = PROVIDERS[provider]
    headers = {"Authorization": f"Bearer {access_token}", "Accept": "application/json"}
    async with httpx.AsyncClient(timeout=15) as client:
        response = await client.get(spec["userinfo_url"], headers=headers)
        if response.status_code != 200:
            raise RuntimeError(f"Profile fetch failed ({response.status_code}).")
        data = response.json()
        profile = {
            "email": data.get("email"),
            "name": data.get("name") or "",
            "avatar": data.get("picture") or data.get("avatar_url") or "",
        }
        if provider == "github" and not profile["email"]:
            emails = await client.get("https://api.github.com/user/emails", headers=headers)
            if emails.status_code == 200:
                profile = pick_primary_email(profile, emails.json())
    return profile


def authorize_url(provider: str, redirect: str, state: str) -> str:
    client_id, _ = provider_credentials(provider)
    spec = PROVIDERS[provider]
    params = {
        "client_id": client_id,
        "redirect_uri": redirect,
        "response_type": "code",
        "scope": spec["scope"],
        "state": state,
        **spec["extra_auth_params"],
    }
    return f"{spec['authorize_url']}?{urlencode(params)}"
