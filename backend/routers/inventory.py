import asyncio
import json
from collections import defaultdict
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

CACHE_TTL_HOURS = 6
_PRICE_SEMAPHORE = asyncio.Semaphore(5)

STEAM_ID_RE = __import__("re").compile(r"^\d{17}$")


async def _fetch_dual_price(name: str) -> tuple[str, dict]:
    async with _PRICE_SEMAPHORE:
        await asyncio.sleep(0.5)
        prices = await get_item_prices_dual(name)
        return name, prices


@router.get("/{steam_id}")
async def fetch_inventory(
    steam_id: str,
    refresh: bool = Query(False),
    db: Session = Depends(get_db),
):
    if not STEAM_ID_RE.match(steam_id):
        raise HTTPException(status_code=400, detail="Invalid Steam ID — must be a 17-digit number.")

    # --- Steam inventory (cached) ---
    cached = db.execute(select(CachedInventory).where(CachedInventory.steam_id == steam_id)).scalar_one_or_none()
    use_cache = (
        cached is not None and not refresh
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
            raise HTTPException(status_code=502, detail="Could not reach Steam. Make sure your inventory is set to Public.")
        if cached:
            cached.items_json = json.dumps(items)
            cached.cached_at = datetime.utcnow()
        else:
            db.add(CachedInventory(steam_id=steam_id, items_json=json.dumps(items)))

    # --- Prices: bulk-load today snapshots, fetch missing concurrently ---
    today  = datetime.utcnow().strftime("%Y-%m-%d")
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    names  = [item["market_hash_name"] for item in items]

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
                db.add(PriceSnapshot(market_hash_name=name, price=best, steam_price=st, date=today))
                existing_snaps[name] = type("snap", (), {"price": best, "steam_price": st})()

    # --- Bulk-load 7-day history in ONE query ---
    all_history_rows = db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.market_hash_name.in_(names))
        .where(PriceSnapshot.date >= cutoff)
        .order_by(PriceSnapshot.date)
    ).scalars().all()

    history_by_name: dict[str, list] = defaultdict(list)
    for row in all_history_rows:
        history_by_name[row.market_hash_name].append({"date": row.date, "price": row.price})

    # --- Ensure watched skins + build response ---
    watched_names = {
        r.market_hash_name
        for r in db.execute(
            select(WatchedSkin).where(WatchedSkin.market_hash_name.in_(names))
        ).scalars().all()
    }
    new_watched = [WatchedSkin(market_hash_name=n, source="inventory") for n in names if n not in watched_names]
    if new_watched:
        db.bulk_save_objects(new_watched)

    enriched = []
    for item in items:
        name = item["market_hash_name"]
        snap = existing_snaps.get(name)
        best_price = snap.price if snap else None
        snap_steam  = snap.steam_price if snap else None
        csfloat_price = None if (snap and snap_steam and snap.price == snap_steam) else best_price
        trend = calculate_7day_trend(history_by_name.get(name, []))
        enriched.append({
            **item,
            "current_price":  best_price,
            "csfloat_price":  csfloat_price,
            "steam_price":    snap_steam,
            "total_value":    round((best_price or 0) * item["quantity"], 2),
            "trend":          trend,
        })

    db.commit()
    return {
        "items":       enriched,
        "total_value": round(sum(i["total_value"] for i in enriched), 2),
        "count":       len(enriched),
        "from_cache":  use_cache,
    }

