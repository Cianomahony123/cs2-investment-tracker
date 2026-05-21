import os
import json
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from db.database import get_db
from db.models import WatchedSkin, PriceSnapshot
from services.trend_analyzer import get_trending_skins, get_ml_trending_skins
from services.csfloat_api import get_item_price

router = APIRouter()

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "popular_skins.json")


@router.get("/")
def get_recommendations(limit: int = 10, db: Session = Depends(get_db)):
    trending = get_trending_skins(db)
    return {
        "recommendations": trending[:limit],
        "generated_at": datetime.utcnow().isoformat(),
        "note": "Ranked by 7-day price trend slope.",
    }


@router.get("/ml-trends")
def get_ml_trends(limit: int = 30, db: Session = Depends(get_db)):
    """ML-based trend analysis over full price history. Ranked by trend_score (slope x R2 + momentum)."""
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
        existing = db.execute(
            select(WatchedSkin).where(WatchedSkin.market_hash_name == name)
        ).scalar_one_or_none()
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
