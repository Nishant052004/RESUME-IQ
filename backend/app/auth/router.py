"""Auth API: register / login / me + OAuth sign-in (Module 8)."""
import secrets

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy.orm import Session

from ..database import get_db
from ..models import User, UserSettings
from . import oauth
from .deps import get_current_user, get_user_settings
from .security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    full_name: str = ""


class LoginIn(BaseModel):
    email: EmailStr
    password: str


def _user_out(user: User, token: str | None = None) -> dict:
    out = {
        "id": user.id,
        "email": user.email,
        "full_name": user.full_name,
        "avatar_url": getattr(user, "avatar_url", "") or "",
    }
    if token is not None:
        out["access_token"] = token
        out["token_type"] = "bearer"
    return out


@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == data.email.lower()).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists.")
    user = User(email=data.email.lower(), full_name=data.full_name.strip(), hashed_password=hash_password(data.password))
    db.add(user)
    db.commit()
    db.refresh(user)
    return _user_out(user, create_access_token(user.id))


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == data.email.lower()).first()
    if user is None or not verify_password(data.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid email or password.")
    return _user_out(user, create_access_token(user.id))


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    return _user_out(user)


# ---------- OAuth (Google / GitHub) ----------

@router.get("/oauth/status")
def oauth_status():
    """Which providers are configured — the UI uses this to style buttons."""
    return {
        "google": oauth.is_configured("google"),
        "github": oauth.is_configured("github"),
    }


@router.get("/oauth/{provider}")
def oauth_start(provider: str, request: Request, origin: str | None = None):
    """Kick off the authorization-code flow. `origin` is the SPA origin the
    callback should return to; it must be allow-listed or it is ignored."""
    if provider not in oauth.PROVIDERS:
        raise HTTPException(status_code=404, detail=f"Unknown OAuth provider '{provider}'.")
    base_url = str(request.base_url)
    fallback = base_url.rstrip("/")
    if not oauth.is_configured(provider):
        return RedirectResponse(f"{fallback}/login?oauth_error=not_configured&provider={provider}", status_code=307)

    target_origin = origin.rstrip("/") if origin else fallback
    if target_origin not in oauth.allowed_origins(base_url):
        target_origin = fallback
    state = oauth.make_state(target_origin)
    url = oauth.authorize_url(provider, oauth.redirect_uri(base_url, provider), state)
    return RedirectResponse(url, status_code=307)


@router.get("/oauth/{provider}/callback")
async def oauth_callback(provider: str, request: Request, code: str = "", state: str = "",
                         db: Session = Depends(get_db)):
    base_url = str(request.base_url)
    fallback = base_url.rstrip("/")

    def back_to_login(reason: str) -> RedirectResponse:
        return RedirectResponse(f"{fallback}/login?oauth_error={reason}&provider={provider}", status_code=307)

    if provider not in oauth.PROVIDERS or not oauth.is_configured(provider):
        return back_to_login("not_configured")
    origin = oauth.verify_state(state, base_url) if state else None
    if origin is None:
        return back_to_login("invalid_state")
    if not code:
        return back_to_login("missing_code")

    try:
        access_token = await oauth.exchange_code(provider, code, oauth.redirect_uri(base_url, provider))
        profile = await oauth.fetch_profile(provider, access_token)
    except RuntimeError:
        return back_to_login("provider_error")

    email = (profile.get("email") or "").lower()
    if not email:
        return back_to_login("no_email")

    user = db.query(User).filter(User.email == email).first()
    if user is None:
        user = User(
            email=email,
            full_name=(profile.get("name") or email.split("@")[0]).strip(),
            # OAuth accounts have no usable password; email/password login stays denied.
            hashed_password=hash_password(secrets.token_urlsafe(32)),
            avatar_url=(profile.get("avatar") or "")[:512],
        )
        db.add(user)
        db.flush()
        db.add(UserSettings(user_id=user.id))
        db.commit()
        db.refresh(user)
    elif (profile.get("avatar") or "") and getattr(user, "avatar_url", "") != profile["avatar"]:
        user.avatar_url = profile["avatar"][:512]  # keep the picture fresh on re-sign-in
        db.commit()

    token = create_access_token(user.id)
    return RedirectResponse(f"{origin}/oauth/callback?token={token}", status_code=302)
