import asyncio
import os
import re
import json
import random
from collections import defaultdict
from fastapi import APIRouter, BackgroundTasks, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from datetime import datetime, timedelta

from db.database import get_db, SessionLocal
from db.models import WatchedSkin, PriceSnapshot
from services.trend_analyzer import get_trending_skins, get_ml_trending_skins
from services.csfloat_api import get_item_price, get_price_history
from utils.rate_limit import rate_limit

router = APIRouter()

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "popular_skins.json")
_BACKFILL_SEMAPHORE = asyncio.Semaphore(3)
_SEED_SEMAPHORE    = asyncio.Semaphore(5)


# ---------------------------------------------------------------------------
# Price filter — mirrors frontend categorize() logic
# ---------------------------------------------------------------------------
def _is_price_exempt(name: str) -> bool:
    """Cases, capsules and stickers are shown regardless of price."""
    if re.search(r"\bCase$", name):    return True
    if "Capsule" in name:              return True
    if name.startswith("Sticker |"):   return True
    return False


def _price_filter(items: list[dict]) -> list[dict]:
    return [
        item for item in items
        if (item.get("current_price") or 0) >= 1 or _is_price_exempt(item["market_hash_name"])
    ]


# ---------------------------------------------------------------------------
# Recommendation endpoints
# ---------------------------------------------------------------------------
@router.get("/")
def get_recommendations(limit: int = 10, db: Session = Depends(get_db)):
    trending = get_trending_skins(db)
    return {
        "recommendations": _price_filter(trending)[:limit],
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/ml-trends")
def get_ml_trends(limit: int = 30, db: Session = Depends(get_db)):
    results = get_ml_trending_skins(db)
    filtered = _price_filter(results)
    return {
        "trends": filtered[:limit],
        "total_analyzed": len(filtered),
        "generated_at": datetime.utcnow().isoformat(),
    }


# ---------------------------------------------------------------------------
# Background price fetcher used by seed
# ---------------------------------------------------------------------------
async def _seed_fetch_prices(names: list[str], today: str) -> None:
    """Fetch today's price for each name concurrently; runs as a background task."""
    async def _fetch_one(name: str):
        async with _SEED_SEMAPHORE:
            await asyncio.sleep(0.3)
            return name, await get_item_price(name)

    results = await asyncio.gather(*[_fetch_one(n) for n in names], return_exceptions=True)

    db = SessionLocal()
    try:
        for item in results:
            if isinstance(item, Exception):
                continue
            name, price = item
            if not price:
                continue
            exists = db.execute(
                select(PriceSnapshot)
                .where(PriceSnapshot.market_hash_name == name)
                .where(PriceSnapshot.date == today)
            ).scalar_one_or_none()
            if not exists:
                db.add(PriceSnapshot(market_hash_name=name, price=price, date=today))
        db.commit()
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Seed watchlist
# ---------------------------------------------------------------------------
@router.post("/seed-watchlist")
async def seed_popular_skins(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    rate_limit(request, max_calls=5, window=3600)

    with open(_DATA_PATH) as f:
        popular: list[str] = json.load(f)

    today = datetime.utcnow().strftime("%Y-%m-%d")

    # 1. Add new skins to watchlist (fast — DB only)
    added = 0
    for name in popular:
        if not db.execute(
            select(WatchedSkin).where(WatchedSkin.market_hash_name == name)
        ).scalar_one_or_none():
            db.add(WatchedSkin(market_hash_name=name, source="watchlist"))
            added += 1
    db.commit()

    # 2. Find which skins still need a price snapshot for today
    existing_today = {
        r for r in db.execute(
            select(PriceSnapshot.market_hash_name)
            .where(PriceSnapshot.market_hash_name.in_(popular))
            .where(PriceSnapshot.date == today)
        ).scalars().all()
    }
    missing = [n for n in popular if n not in existing_today]

    # 3. Fetch prices in the background — response returns immediately
    if missing:
        background_tasks.add_task(_seed_fetch_prices, missing, today)

    return {
        "added_to_watchlist": added,
        "total_seeded": len(popular),
        "prices_queued": len(missing),
    }


# ---------------------------------------------------------------------------
# Backfill history
# ---------------------------------------------------------------------------
@router.post("/backfill")
async def backfill_history(request: Request, db: Session = Depends(get_db)):
    rate_limit(request, max_calls=2, window=3600)
    names = list(db.execute(select(distinct(PriceSnapshot.market_hash_name))).scalars().all())
    if not names:
        return {"message": "No skins tracked yet. Run seed-watchlist first.", "filled": 0, "skins_processed": 0}

    existing_dates: dict[str, set] = defaultdict(set)
    for row in db.execute(select(PriceSnapshot.market_hash_name, PriceSnapshot.date)).all():
        existing_dates[row.market_hash_name].add(row.date)

    today_snaps = {
        r.market_hash_name: r.price
        for r in db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.date == datetime.utcnow().strftime("%Y-%m-%d"))
        ).scalars().all()
    }

    real_filled = 0
    synthetic_filled = 0

    async def _backfill_one(name: str):
        nonlocal real_filled, synthetic_filled
        async with _BACKFILL_SEMAPHORE:
            await asyncio.sleep(0.4)
            history = await get_price_history(name)
            by_date: dict[str, list] = defaultdict(list)
            for entry in history:
                raw = entry.get("date", "")
                ds = raw[:10] if len(raw) >= 10 else None
                if ds and ds not in existing_dates[name]:
                    by_date[ds].append(entry["price"])

            if by_date:
                for ds, prices in by_date.items():
                    avg = round(sum(prices) / len(prices), 2)
                    db.add(PriceSnapshot(market_hash_name=name, price=avg, date=ds))
                    existing_dates[name].add(ds)
                    real_filled += 1
            else:
                base = today_snaps.get(name)
                if not base:
                    return
                rng = random.Random(hash(name))
                price = base
                for days_back in range(14, 0, -1):
                    ds = (datetime.utcnow() - timedelta(days=days_back)).strftime("%Y-%m-%d")
                    if ds in existing_dates[name]:
                        price = base
                        continue
                    change = rng.uniform(-0.03, 0.03)
                    price = round(max(price * (1 + change), 0.01), 2)
                    db.add(PriceSnapshot(market_hash_name=name, price=price, date=ds))
                    existing_dates[name].add(ds)
                    synthetic_filled += 1

    await asyncio.gather(*[_backfill_one(n) for n in names])
    db.commit()
    return {
        "filled":              real_filled + synthetic_filled,
        "real_snapshots":      real_filled,
        "synthetic_snapshots": synthetic_filled,
        "skins_processed":     len(names),
    }
