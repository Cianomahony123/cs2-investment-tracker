import numpy as np
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import select, distinct
from db.models import PriceSnapshot


def calculate_7day_trend(snapshots: list[dict]) -> dict:
    """Linear regression trend over a 7-day window."""
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


def _r_squared(prices: np.ndarray, x: np.ndarray, coeffs) -> float:
    y_pred = np.polyval(coeffs, x)
    ss_res = np.sum((prices - y_pred) ** 2)
    ss_tot = np.sum((prices - np.mean(prices)) ** 2)
    return float(1 - ss_res / ss_tot) if ss_tot > 0 else 0.0


def analyze_ml_trend(snapshots: list[dict]) -> dict:
    """
    ML-based trend analysis over the full available price history.

    Returns slope, R² confidence, momentum (trend acceleration),
    and a composite trend_score = slope_pct * r_squared.
    """
    if len(snapshots) < 3:
        return None

    sorted_snaps = sorted(snapshots, key=lambda x: x["date"])
    prices = np.array([s["price"] for s in sorted_snaps], dtype=float)
    x = np.arange(len(prices))
    baseline = prices[0] if prices[0] > 0 else 1.0

    # Linear regression
    coeffs = np.polyfit(x, prices, 1)
    slope = coeffs[0]
    slope_pct = float(slope / baseline) * 100
    r2 = _r_squared(prices, x, coeffs)

    # Momentum: compare slope of first half vs second half
    mid = len(prices) // 2
    momentum = 0.0
    if mid >= 2 and len(prices) - mid >= 2:
        s_first = np.polyfit(np.arange(mid), prices[:mid], 1)[0]
        s_second = np.polyfit(np.arange(len(prices) - mid), prices[mid:], 1)[0]
        momentum = float((s_second - s_first) / baseline) * 100

    # Volatility (coefficient of variation)
    volatility = float(np.std(prices) / np.mean(prices)) * 100 if np.mean(prices) > 0 else 0.0

    # Composite trend score: slope strength × confidence, boosted by positive momentum
    trend_score = round(slope_pct * max(r2, 0) + momentum * 0.3, 4)

    total_change_pct = round(float((prices[-1] - prices[0]) / baseline) * 100, 2)

    # Human-readable classification
    if trend_score > 2:
        classification = "Strong Uptrend"
    elif trend_score > 0.5:
        classification = "Uptrend"
    elif trend_score < -2:
        classification = "Strong Downtrend"
    elif trend_score < -0.5:
        classification = "Downtrend"
    else:
        classification = "Sideways"

    return {
        "slope_pct": round(slope_pct, 4),
        "r_squared": round(r2, 4),
        "momentum": round(momentum, 4),
        "volatility_pct": round(volatility, 2),
        "trend_score": trend_score,
        "classification": classification,
        "total_change_pct": total_change_pct,
        "data_points": len(prices),
        "current_price": round(float(prices[-1]), 2),
        "start_price": round(float(prices[0]), 2),
        "date_range": f"{sorted_snaps[0]['date']} – {sorted_snaps[-1]['date']}",
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


def get_ml_trending_skins(db: Session, min_data_points: int = 3) -> list[dict]:
    """
    ML trend analysis over the full available price history for all tracked skins.
    Ranked by composite trend_score (slope × R² + momentum boost).
    """
    names = db.execute(select(distinct(PriceSnapshot.market_hash_name))).scalars().all()

    results = []
    for name in names:
        snaps = db.execute(
            select(PriceSnapshot)
            .where(PriceSnapshot.market_hash_name == name)
            .order_by(PriceSnapshot.date)
        ).scalars().all()

        if len(snaps) < min_data_points:
            continue

        ml = analyze_ml_trend([{"date": s.date, "price": s.price} for s in snaps])
        if ml:
            results.append({"market_hash_name": name, **ml})

    results.sort(key=lambda x: x["trend_score"], reverse=True)
    return results
