import asyncio
import json
from fastapi import APIRouter, HTTPException, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime, timedelta

from services.steam_api import get_inventory
from services.csfloat_api import get_item_prices_dual
from services.trend_analyzer import calculate_7day_trend
from db.database import get_db
from db.models import PriceSnapshot, WatchedSkin, CachedInventory

router = APIRouter()

CACHE_TTL_HOURS = 1
_PRICE_SEMAPHORE = asyncio.Semaphore(5)


async def _fetch_dual_price(name: str) -> tuple[str, dict]:
    async with _PRICE_SEMAPHORE:
        await asyncio.sleep(0.2)
        prices = await get_item_prices_dual(name)
        return name, prices


@router.get("/{steam_id}")
async def fetch_inventory(
    steam_id: str,
    refresh: bool = Query(False, description="Force re-fetch from Steam, ignoring cache"),
    db: Session = Depends(get_db),
):
    # --- Steam inventory (cached) ---
    cached = db.execute(
        select(CachedInventory).where(CachedInventory.steam_id == steam_id)
    ).scalar_one_or_none()

    use_cache = (
        cached is not None
        and not refresh
        and (datetime.utcnow() - cached.cached_at).total_seconds() < CACHE_TTL_HOURS * 3600
    )

    if use_cache:
        items = json.loads(cached.items_json)
    else:
        try:
            items = await get_inventory(steam_id)
        except (ValueError, IOError) as e:
            raise HTTPException(status_code=400, detail=str(e))
        except Exception:
            raise HTTPException(
                status_code=502,
                detail="Could not reach Steam. Make sure your Steam ID is correct and your inventory is set to Public.",
            )

        if cached:
            cached.items_json = json.dumps(items)
            cached.cached_at = datetime.utcnow()
        else:
            db.add(CachedInventory(steam_id=steam_id, items_json=json.dumps(items)))

    # --- Prices: bulk-load today snapshots, fetch missing ones concurrently ---
    today = datetime.utcnow().strftime("%Y-%m-%d")
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    names = [item["market_hash_name"] for item in items]

    existing_snaps = {
        s.market_hash_name: s
        for s in db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.market_hash_name.in_(names))
            .where(PriceSnapshot.date == today)
        ).scalars().all()
    }

    missing = [n for n in names if n not in existing_snaps]
    if missing:
        fetched = await asyncio.gather(*[_fetch_dual_price(n) for n in missing])
        for name, prices in fetched:
            cf = prices["csfloat_price"]
            st = prices["steam_price"]
            best = cf or st
            if best:
                new_snap = PriceSnapshot(
                    market_hash_name=name,
                    price=best,
                    steam_price=st,
                    date=today,
                )
                db.add(new_snap)
                existing_snaps[name] = new_snap

    # --- Ensure watched skins + compute trends + build response ---
    enriched = []
    for item in items:
        name = item["market_hash_name"]

        watched = db.execute(
            select(WatchedSkin).where(WatchedSkin.market_hash_name == name)
        ).scalar_one_or_none()
        if not watched:
            db.add(WatchedSkin(market_hash_name=name, source="inventory"))

        snap = existing_snaps.get(name)
        best_price = snap.price if snap else None
        # Derive CSFloat price: if snap.price equals steam_price, we stored the fallback
        snap_steam = snap.steam_price if snap else None
        if snap and snap_steam and snap.price == snap_steam:
            csfloat_price = None   # Only Steam was available when we stored
        else:
            csfloat_price = best_price
        steam_price = snap_steam

        history = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.market_hash_name == name)
            .where(PriceSnapshot.date >= cutoff)
            .order_by(PriceSnapshot.date)
        ).scalars().all()

        trend = calculate_7day_trend([{"date": s.date, "price": s.price} for s in history])

        enriched.append({
            **item,
            "current_price": best_price,
            "csfloat_price": csfloat_price,
            "steam_price": steam_price,
            "total_value": round((best_price or 0) * item["quantity"], 2),
            "trend": trend,
        })

    db.commit()

    total_value = sum(i["total_value"] for i in enriched)
    return {
        "items": enriched,
        "total_value": round(total_value, 2),
        "count": len(enriched),
        "from_cache": use_cache,
    }
