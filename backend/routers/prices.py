from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from db.database import get_db
from db.models import PriceSnapshot
from services.csfloat_api import get_price_history, get_item_price
from utils.rate_limit import rate_limit

router = APIRouter()

_MAX_NAME_LEN = 200


@router.get("/{market_hash_name:path}/history")
async def price_history(market_hash_name: str, db: Session = Depends(get_db)):
    if len(market_hash_name) > _MAX_NAME_LEN:
        raise HTTPException(status_code=400, detail="market_hash_name too long")
    snaps = db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.market_hash_name == market_hash_name)
        .order_by(PriceSnapshot.date)
    ).scalars().all()

    stored = [{"date": s.date, "price": s.price} for s in snaps]
    sold = await get_price_history(market_hash_name)

    return {
        "market_hash_name": market_hash_name,
        "stored_history":   stored,
        "sold_history":     sold,
    }


@router.post("/{market_hash_name:path}/snapshot")
async def force_snapshot(request: Request, market_hash_name: str, db: Session = Depends(get_db)):
    if len(market_hash_name) > _MAX_NAME_LEN:
        raise HTTPException(status_code=400, detail="market_hash_name too long")
    rate_limit(request, max_calls=20, window=60)

    price = await get_item_price(market_hash_name)
    if price is None:
        raise HTTPException(status_code=404, detail="Price not found on CSFloat")

    today = datetime.utcnow().strftime("%Y-%m-%d")
    snap = db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.market_hash_name == market_hash_name)
        .where(PriceSnapshot.date == today)
    ).scalar_one_or_none()

    if snap:
        snap.price = price
    else:
        db.add(PriceSnapshot(market_hash_name=market_hash_name, price=price, date=today))

    db.commit()
    return {"market_hash_name": market_hash_name, "price": price, "date": today}
