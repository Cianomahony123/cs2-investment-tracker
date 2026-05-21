import asyncio
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


def _cf_headers() -> dict:
    return {"Authorization": _API_KEY} if _API_KEY else {}


async def get_item_listings(market_hash_name: str, limit: int = 10) -> dict:
    async with httpx.AsyncClient(timeout=20.0) as client:
        resp = await client.get(
            f"{CSFLOAT_BASE}/listings",
            params={"market_hash_name": market_hash_name, "limit": limit, "sort_by": "lowest_price"},
            headers=_cf_headers(),
        )
        resp.raise_for_status()
        return resp.json()


async def _get_csfloat_price(market_hash_name: str) -> Optional[float]:
    try:
        data = await get_item_listings(market_hash_name, limit=5)
        listings = data.get("data", [])
        if listings:
            prices = [l["price"] / 100 for l in listings if "price" in l]
            if prices:
                return round(min(prices), 2)
    except Exception:
        pass
    return None


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


async def get_item_prices_dual(market_hash_name: str) -> dict:
    """Fetch CSFloat and Steam Market prices concurrently. Returns {csfloat_price, steam_price}."""
    csfloat_price, steam_price = await asyncio.gather(
        _get_csfloat_price(market_hash_name),
        _get_steam_market_price(market_hash_name),
    )
    return {"csfloat_price": csfloat_price, "steam_price": steam_price}


async def get_item_price(market_hash_name: str) -> Optional[float]:
    """Best available price: CSFloat first, Steam Market fallback."""
    prices = await get_item_prices_dual(market_hash_name)
    return prices["csfloat_price"] or prices["steam_price"]


async def get_price_history(market_hash_name: str) -> list[dict]:
    try:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.get(
                f"{CSFLOAT_BASE}/listings",
                params={"market_hash_name": market_hash_name, "limit": 50, "sort_by": "most_recent", "type": "sold"},
                headers=_cf_headers(),
            )
            resp.raise_for_status()
            data = resp.json()
        return [
            {"price": l["price"] / 100, "date": l.get("sold_at", l.get("created_at", ""))}
            for l in data.get("data", [])
            if "price" in l
        ]
    except Exception:
        return []
