import os
import httpx
from typing import Optional
from dotenv import load_dotenv

load_dotenv()

CSFLOAT_BASE = "https://csfloat.com/api/v1"
_API_KEY = os.getenv("CSFLOAT_API_KEY", "")


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


async def get_item_price(market_hash_name: str) -> Optional[float]:
    try:
        data = await get_item_listings(market_hash_name, limit=5)
        listings = data.get("data", [])
        if not listings:
            return None
        prices = [listing["price"] / 100 for listing in listings if "price" in listing]
        return round(min(prices), 2) if prices else None
    except Exception:
        return None


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
