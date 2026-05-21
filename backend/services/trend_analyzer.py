import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from db.models import PriceSnapshot


def calculate_7day_trend(snapshots: list[dict]) -> dict:
    """
    Returns trend metrics over a 7-day window.
    snapshots: list of {"date": "YYYY-MM-DD", "price": float}
    """
    if len(snapshots) < 2:
        return {
            "slope_pct": 0.0,
            "total_change_pct": 0.0,
            "data_points": len(snapshots),
            "current_price": snapshots[0]["price"] if snapshots else None,
            "start_price": snapshots[0]["price"] if snapshots else None,
        }

    sorted_snaps = sorted(snapshots, key=lambda x: x["date"])
    prices = np.array([s["price"] for s in sorted_snaps], dtype=float)
    x = np.arange(len(prices))

    coeffs = np.polyfit(x, prices, 1)
    slope = coeffs[0]
    baseline = prices[0] if prices[0] > 0 else 1.0

    return {
        "slope_pct": round(float(slope / baseline) * 100, 4),
        "total_change_pct": round(float((prices[-1] - prices[0]) / baseline) * 100, 2),
        "data_points": len(prices),
        "current_price": round(float(prices[-1]), 2),
        "start_price": round(float(prices[0]), 2),
    }


def get_trending_skins(db: Session, min_data_points: int = 3) -> list[dict]:
    """Rank all tracked skins by 7-day trend slope, highest first."""
    cutoff = (datetime.utcnow() - timedelta(days=7)).strftime("%Y-%m-%d")
    names = db.execute(select(distinct(PriceSnapshot.market_hash_name))).scalars().all()

    results = []
    for name in names:
        snaps = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.market_hash_name == name)
            .where(PriceSnapshot.date >= cutoff)
            .order_by(PriceSnapshot.date)
        ).scalars().all()

        if len(snaps) < min_data_points:
            continue

        trend = calculate_7day_trend([{"date": s.date, "price": s.price} for s in snaps])
        results.append({"market_hash_name": name, **trend})

    results.sort(key=lambda x: x["slope_pct"], reverse=True)
    return results
