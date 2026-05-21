from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import select
from datetime import datetime

from db.database import get_db
from db.models import PriceSnapshot
from services.csfloat_api import get_price_history, get_item_price

router = APIRouter()


@router.get("/{market_hash_name:path}/history")
async def price_history(market_hash_name: str, db: Session = Depends(get_db)):
    snaps = db.execute(
        select(PriceSnapshot)
        .where(PriceSnapshot.market_hash_name == market_hash_name)
        .order_by(PriceSnapshot.date)
    ).scalars().all()

    stored = [{"date": s.date, "price": s.price} for s in snaps]
    sold = await get_price_history(market_hash_name)

    return {
        "market_hash_name": market_hash_name,
        "stored_history": stored,
        "sold_history": sold,
    }


@router.post("/{market_hash_name:path}/snapshot")
async def force_snapshot(market_hash_name: str, db: Session = Depends(get_db)):
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
