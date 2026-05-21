import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

CSFLOAT_BASE = "https://csfloat.com/api/v1"
STEAM_MARKET_BASE = "https://steamcommunity.com/market/priceoverview"
_API_KEY = os.getenv("CSFLOAT_API_KEY", "")

_STEAM_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Accept": "application/json",
    "Referer": "https://steamcommunity.com/market/",
}


def _headers() -> dict:
    return {"Authorization": _API_KEY} if _API_KEY else {}


async def get_item_listings(market_hash_name: str, limit: int = 10) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{CSFLOAT_BASE}/listings",
            params={
                "market_hash_name": market_hash_name,
                "limit": limit,
                "sort_by": "lowest_price",
            },
            headers=_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def _get_steam_market_price(market_hash_name: str) -> Optional[float]:
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=_STEAM_HEADERS) as client:
            resp = await client.get(
                STEAM_MARKET_BASE,
                params={"country": "US", "currency": 1, "appid": 730, "market_hash_name": market_hash_name},
            )
            resp.raise_for_status()
            data = resp.json()
        if not data.get("success"):
            return None
        for key in ("median_price", "lowest_price"):
            raw = data.get(key, "")
            if raw:
                cleaned = raw.replace("$", "").replace(",", "").strip()
                try:
                    return round(float(cleaned), 2)
                except ValueError:
                    continue
        return None
    except Exception:
        return None


async def get_item_price(market_hash_name: str) -> Optional[float]:
    try:
        data = await get_item_listings(market_hash_name, limit=5)
        listings = data.get("data", [])
        if listings:
            prices = [listing["price"] / 100 for listing in listings if "price" in listing]
            if prices:
                return round(min(prices), 2)
    except Exception:
        pass
    # CSFloat failed or returned no listings — fall back to Steam Market
    return await _get_steam_market_price(market_hash_name)


async def get_price_history(market_hash_name: str) -> list[dict]:
    """Uses recent sold listings as a proxy for price history."""
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{CSFLOAT_BASE}/listings",
                params={
                    "market_hash_name": market_hash_name,
                    "limit": 50,
                    "sort_by": "most_recent",
                    "type": "sold",
                },
                headers=_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            {
                "price": listing["price"] / 100,
                "date": listing.get("sold_at", listing.get("created_at", "")),
            }
            for listing in data.get("data", [])
            if "price" in listing
        ]
    except Exception:
        return []
