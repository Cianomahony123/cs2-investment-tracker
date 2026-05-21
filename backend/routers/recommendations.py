import asyncio
import os
import json
import random
from collections import defaultdict
from fastapi import APIRouter, Depends, Request
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from datetime import datetime, timedelta

from db.database import get_db
from db.models import WatchedSkin, PriceSnapshot
from services.trend_analyzer import get_trending_skins, get_ml_trending_skins
from services.csfloat_api import get_item_price, get_price_history
from utils.rate_limit import rate_limit

router = APIRouter()

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "popular_skins.json")
_BACKFILL_SEMAPHORE = asyncio.Semaphore(3)


@router.get("/")
def get_recommendations(limit: int = 10, db: Session = Depends(get_db)):
    trending = get_trending_skins(db)
    return {"recommendations": trending[:limit], "generated_at": datetime.utcnow().isoformat()}


@router.get("/ml-trends")
def get_ml_trends(limit: int = 30, db: Session = Depends(get_db)):
    results = get_ml_trending_skins(db)
    return {"trends": results[:limit], "total_analyzed": len(results), "generated_at": datetime.utcnow().isoformat()}


@router.post("/seed-watchlist")
async def seed_popular_skins(request: Request, db: Session = Depends(get_db)):
    rate_limit(request, max_calls=5, window=3600)
    with open(_DATA_PATH) as f:
        popular: list[str] = json.load(f)
    today = datetime.utcnow().strftime("%Y-%m-%d")
    added = 0
    for name in popular:
        if not db.execute(select(WatchedSkin).where(WatchedSkin.market_hash_name == name)).scalar_one_or_none():
            db.add(WatchedSkin(market_hash_name=name, source="watchlist"))
            added += 1
        if not db.execute(select(PriceSnapshot).where(PriceSnapshot.market_hash_name == name).where(PriceSnapshot.date == today)).scalar_one_or_none():
            price = await get_item_price(name)
            if price:
                db.add(PriceSnapshot(market_hash_name=name, price=price, date=today))
    db.commit()
    return {"added_to_watchlist": added, "total_seeded": len(popular)}


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
