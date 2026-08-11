"""
Google OAuth 2.0 authentication + JWT session management.

Endpoints:
  GET /auth/google/login    → redirect to Google consent screen
  GET /auth/google/callback → exchange code, issue JWT cookie
  GET /auth/me              → return current user info
  GET /auth/logout          → clear session cookie
"""
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from jose import JWTError, jwt
import httpx

from config import get_settings
from database import get_db
from db_models import User

router = APIRouter(prefix="/auth", tags=["auth"])
settings = get_settings()

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO_URL = "https://www.googleapis.com/oauth2/v3/userinfo"

COOKIE_NAME = "finscope_session"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _create_jwt(user_id: str) -> str:
    """Create a signed JWT with user_id as subject."""
    payload = {
        "sub": user_id,
        "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.jwt_expire_minutes),
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def _set_session_cookie(response: Response, token: str):
    """Set the session JWT as an httpOnly cookie."""
    is_production = not settings.backend_url.startswith("http://localhost")
    response.set_cookie(
        key=COOKIE_NAME,
        value=token,
        httponly=True,
        secure=is_production,
        samesite="none" if is_production else "lax",
        max_age=settings.jwt_expire_minutes * 60,
        path="/",
    )


def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
    """FastAPI dependency — extract the authenticated user from the session cookie."""
    token = request.cookies.get(COOKIE_NAME)
    if not token:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(status_code=401, detail="Invalid token")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=401, detail="User not found")

    return user


def get_optional_user(request: Request, db: Session = Depends(get_db)):
    """Like get_current_user but returns None instead of raising 401."""
    try:
        return get_current_user(request, db)
    except HTTPException:
        return None


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("/google/login")
def google_login():
    """Redirect the user to Google's OAuth consent screen."""
    redirect_uri = f"{settings.backend_url}/auth/google/callback"
    params = {
        "client_id": settings.google_client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid email profile",
        "access_type": "offline",
        "prompt": "consent",
    }
    query = "&".join(f"{k}={v}" for k, v in params.items())
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/google/callback")
async def google_callback(code: str, db: Session = Depends(get_db)):
    """Exchange the authorization code for tokens, upsert the user, issue a session cookie."""
    redirect_uri = f"{settings.backend_url}/auth/google/callback"

    # Exchange code for tokens
    async with httpx.AsyncClient() as client:
        token_response = await client.post(
            GOOGLE_TOKEN_URL,
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )

    if token_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to exchange code for tokens")

    tokens = token_response.json()
    access_token = tokens.get("access_token")

    # Fetch user info
    async with httpx.AsyncClient() as client:
        userinfo_response = await client.get(
            GOOGLE_USERINFO_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

    if userinfo_response.status_code != 200:
        raise HTTPException(status_code=400, detail="Failed to fetch user info")

    userinfo = userinfo_response.json()
    google_sub = userinfo["sub"]
    email = userinfo["email"]
    name = userinfo.get("name", "")
    picture = userinfo.get("picture", "")

    # Upsert user
    user = db.query(User).filter(User.google_sub == google_sub).first()
    if user is None:
        user = User(google_sub=google_sub, email=email, name=name, picture=picture)
        db.add(user)
        db.commit()
        db.refresh(user)
    else:
        user.name = name
        user.picture = picture
        db.commit()

    # Issue JWT and redirect to frontend
    token = _create_jwt(user.id)
    response = RedirectResponse(url=settings.frontend_origin)
    _set_session_cookie(response, token)
    return response


@router.get("/me")
def me(user: User = Depends(get_current_user)):
    """Return the current authenticated user's info."""
    return {
        "id": user.id,
        "email": user.email,
        "name": user.name,
        "picture": user.picture,
    }


@router.get("/logout")
def logout():
    """Clear the session cookie."""
    response = RedirectResponse(url=settings.frontend_origin)
    response.delete_cookie(COOKIE_NAME, path="/")
    return response
