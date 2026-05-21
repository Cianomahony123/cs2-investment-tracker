import asyncio
import os
import json
from collections import defaultdict
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from datetime import datetime

from db.database import get_db
from db.models import WatchedSkin, PriceSnapshot
from services.trend_analyzer import get_trending_skins, get_ml_trending_skins
from services.csfloat_api import get_item_price, get_price_history

router = APIRouter()

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "popular_skins.json")
_BACKFILL_SEMAPHORE = asyncio.Semaphore(3)


@router.get("/")
def get_recommendations(limit: int = 10, db: Session = Depends(get_db)):
    trending = get_trending_skins(db)
    return {
        "recommendations": trending[:limit],
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.get("/ml-trends")
def get_ml_trends(limit: int = 30, db: Session = Depends(get_db)):
    results = get_ml_trending_skins(db)
    return {
        "trends": results[:limit],
        "total_analyzed": len(results),
        "generated_at": datetime.utcnow().isoformat(),
    }


@router.post("/seed-watchlist")
async def seed_popular_skins(db: Session = Depends(get_db)):
    with open(_DATA_PATH) as f:
        popular: list[str] = json.load(f)

    today = datetime.utcnow().strftime("%Y-%m-%d")
    added = 0
    for name in popular:
        existing = db.execute(select(WatchedSkin).where(WatchedSkin.market_hash_name == name)).scalar_one_or_none()
        if not existing:
            db.add(WatchedSkin(market_hash_name=name, source="watchlist"))
            added += 1

        snap = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.market_hash_name == name)
            .where(PriceSnapshot.date == today)
        ).scalar_one_or_none()
        if not snap:
            price = await get_item_price(name)
            if price:
                db.add(PriceSnapshot(market_hash_name=name, price=price, date=today))

    db.commit()
    return {"added_to_watchlist": added, "total_seeded": len(popular)}


@router.post("/backfill")
async def backfill_history(db: Session = Depends(get_db)):
    """
    Populate multi-day price history immediately by mining CSFloat sold-listing timestamps.
    Each sold listing carries a real sale date — we group by day to build authentic snapshots.
    """
    names = db.execute(select(distinct(PriceSnapshot.market_hash_name))).scalars().all()
    if not names:
        return {"message": "No skins tracked yet. Run seed-watchlist first.", "filled": 0}

    existing_dates: dict[str, set] = defaultdict(set)
    for row in db.execute(select(PriceSnapshot.market_hash_name, PriceSnapshot.date)).all():
        existing_dates[row.market_hash_name].add(row.date)

    filled = 0
    errors = 0

    async def _backfill_one(name: str):
        nonlocal filled, errors
        async with _BACKFILL_SEMAPHORE:
            await asyncio.sleep(0.4)
            try:
                history = await get_price_history(name)
                by_date: dict[str, list] = defaultdict(list)
                for entry in history:
                    raw_date = entry.get("date", "")
                    date_str = raw_date[:10] if len(raw_date) >= 10 else None
                    if date_str and date_str not in existing_dates[name]:
                        by_date[date_str].append(entry["price"])
                for date_str, prices in by_date.items():
                    avg = round(sum(prices) / len(prices), 2)
                    db.add(PriceSnapshot(market_hash_name=name, price=avg, date=date_str))
                    existing_dates[name].add(date_str)
                    filled += 1
            except Exception:
                errors += 1

    await asyncio.gather(*[_backfill_one(n) for n in names])
    db.commit()
    return {"filled": filled, "skins_processed": len(names), "errors": errors}
