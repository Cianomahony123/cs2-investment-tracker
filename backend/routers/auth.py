import os
import re
import httpx
from urllib.parse import urlencode, parse_qs
from fastapi import APIRouter, Request, HTTPException
from fastapi.responses import RedirectResponse
from dotenv import load_dotenv

load_dotenv()

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")
BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
STEAM_OPENID = "https://steamcommunity.com/openid/login"
STEAM_ID_RE = re.compile(r"https://steamcommunity\.com/openid/id/(\d+)")

router = APIRouter()


@router.get("/steam")
def login_with_steam():
    params = {
        "openid.ns": "http://specs.openid.net/auth/2.0",
        "openid.mode": "checkid_setup",
        "openid.return_to": f"{BACKEND_URL}/api/auth/callback",
        "openid.realm": BACKEND_URL,
        "openid.identity": "http://specs.openid.net/auth/2.0/identifier_select",
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

    # Verify with Steam
    verify_params = {**params, "openid.mode": "check_authentication"}
    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.post(STEAM_OPENID, data=verify_params)

    if "is_valid:true" not in resp.text:
        raise HTTPException(status_code=401, detail="Steam authentication could not be verified.")

    steam_id = match.group(1)
    return RedirectResponse(f"{FRONTEND_URL}/?steam_id={steam_id}")
