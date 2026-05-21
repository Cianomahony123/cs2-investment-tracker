import os
import re
import hmac
import time
import secrets
import hashlib
import jwt
import httpx
from urllib.parse import urlencode, parse_qs
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from fastapi import Depends
from db.database import get_db
from db.models import GoogleUser
from dotenv import load_dotenv

load_dotenv()

FRONTEND_URL  = os.getenv("FRONTEND_URL",  "http://localhost:5173")
BACKEND_URL   = os.getenv("BACKEND_URL",   "http://localhost:8000")
SECRET_KEY    = os.getenv("SECRET_KEY",    "dev-secret-change-me-in-prod")
GOOGLE_CLIENT_ID     = os.getenv("GOOGLE_CLIENT_ID",     "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")

STEAM_OPENID   = "https://steamcommunity.com/openid/login"
STEAM_ID_RE    = re.compile(r"https://steamcommunity\.com/openid/id/(\d{17})")
STEAM_ID_VALID = re.compile(r"^\d{17}$")

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"

router = APIRouter()


# ── helpers ──────────────────────────────────────────────────────────────────

def _make_state() -> str:
    nonce = secrets.token_urlsafe(16)
    ts = str(int(time.time()))
    sig = hmac.new(SECRET_KEY.encode(), f"{nonce}:{ts}".encode(), hashlib.sha256).hexdigest()[:16]
    return f"{nonce}:{ts}:{sig}"


def _verify_state(state: str) -> bool:
    parts = state.split(":")
    if len(parts) != 3:
        return False
    nonce, ts_str, sig = parts
    try:
        age = time.time() - int(ts_str)
    except ValueError:
        return False
    if age > 300:  # 5-minute window
        return False
    expected = hmac.new(SECRET_KEY.encode(), f"{nonce}:{ts_str}".encode(), hashlib.sha256).hexdigest()[:16]
    return hmac.compare_digest(sig, expected)


def _issue_token(payload: dict) -> str:
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")


# ── auth config ───────────────────────────────────────────────────────────────

@router.get("/config")
def auth_config():
    return {
        "steam":  True,
        "google": bool(GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET),
    }


# ── Steam ─────────────────────────────────────────────────────────────────────

@router.get("/steam")
def login_with_steam():
    params = {
        "openid.ns":         "http://specs.openid.net/auth/2.0",
        "openid.mode":       "checkid_setup",
        "openid.return_to":  f"{BACKEND_URL}/api/auth/callback",
        "openid.realm":      BACKEND_URL,
        "openid.identity":   "http://specs.openid.net/auth/2.0/identifier_select",
        "openid.claimed_id": "http://specs.openid.net/auth/2.0/identifier_select",
    }
    return RedirectResponse(f"{STEAM_OPENID}?{urlencode(params)}")


@router.get("/callback")
async def auth_callback(request: Request):
    params = dict(request.query_params)
    if params.get("openid.mode") != "id_res":
        raise HTTPException(status_code=400, detail="Steam login cancelled or failed.")

    claimed_id = params.get("openid.claimed_id", "")
    match = STEAM_ID_RE.match(claimed_id)
    if not match:
        raise HTTPException(status_code=400, detail="Invalid Steam ID in response.")

    verify_params = {**params, "openid.mode": "check_authentication"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(STEAM_OPENID, data=verify_params)

    if "is_valid:true" not in resp.text:
        raise HTTPException(status_code=401, detail="Steam authentication could not be verified.")

    steam_id = match.group(1)
    return RedirectResponse(f"{FRONTEND_URL}/?steam_id={steam_id}")


# ── Google ────────────────────────────────────────────────────────────────────

@router.get("/google")
def login_with_google():
    if not GOOGLE_CLIENT_ID:
        raise HTTPException(status_code=503, detail="Google login is not configured.")
    state = _make_state()
    params = {
        "client_id":     GOOGLE_CLIENT_ID,
        "redirect_uri":  f"{BACKEND_URL}/api/auth/google/callback",
        "response_type": "code",
        "scope":         "openid email profile",
        "state":         state,
        "access_type":   "online",
    }
    return RedirectResponse(f"{GOOGLE_AUTH_URL}?{urlencode(params)}")


@router.get("/google/callback")
async def google_callback(request: Request, db: Session = Depends(get_db)):
    params = dict(request.query_params)

    state = params.get("state", "")
    if not _verify_state(state):
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state.")

    code = params.get("code")
    if not code:
        raise HTTPException(status_code=400, detail="Google login cancelled or failed.")

    # Exchange code for tokens
    async with httpx.AsyncClient(timeout=15.0) as client:
        token_resp = await client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "redirect_uri":  f"{BACKEND_URL}/api/auth/google/callback",
            "grant_type":    "authorization_code",
        })

    if token_resp.status_code != 200:
        raise HTTPException(status_code=401, detail="Failed to exchange Google auth code.")

    id_token_str = token_resp.json().get("id_token")
    if not id_token_str:
        raise HTTPException(status_code=401, detail="No ID token in Google response.")

    # Decode without verification (Google already verified via HTTPS)
    try:
        claims = jwt.decode(id_token_str, options={"verify_signature": False})
    except Exception:
        raise HTTPException(status_code=401, detail="Failed to decode Google ID token.")

    google_id = claims.get("sub")
    email     = claims.get("email", "")
    name      = claims.get("name", email)
    picture   = claims.get("picture", "")

    if not google_id:
        raise HTTPException(status_code=401, detail="Missing user ID in Google token.")

    # Upsert user in DB
    from sqlalchemy import select
    user = db.execute(select(GoogleUser).where(GoogleUser.google_id == google_id)).scalar_one_or_none()
    if user:
        user.name    = name
        user.picture = picture
        from datetime import datetime
        user.last_login = datetime.utcnow()
    else:
        db.add(GoogleUser(google_id=google_id, email=email, name=name, picture=picture))
    db.commit()

    # Issue a signed JWT for the frontend
    token = _issue_token({"sub": google_id, "email": email, "name": name, "picture": picture})
    return RedirectResponse(f"{FRONTEND_URL}/?google_token={token}")


# ── Steam profile ─────────────────────────────────────────────────────────────

@router.get("/steam/profile/{steam_id}")
async def steam_profile(steam_id: str):
    if not STEAM_ID_VALID.match(steam_id):
        raise HTTPException(status_code=400, detail="Invalid Steam ID")
    url = f"https://steamcommunity.com/profiles/{steam_id}/?xml=1"
    _hdr = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36",
    }
    try:
        async with httpx.AsyncClient(timeout=10.0, headers=_hdr) as client:
            resp = await client.get(url)
        import xml.etree.ElementTree as ET
        root   = ET.fromstring(resp.text)
        name   = root.findtext("steamID")   or f"…{steam_id[-6:]}"
        avatar = root.findtext("avatarFull") or root.findtext("avatarMedium") or ""
    except Exception:
        name   = f"…{steam_id[-6:]}"
        avatar = ""
    return {"steam_id": steam_id, "name": name, "avatar": avatar}
