# CS2 Investment Tracker

Track your CS2 skin portfolio using CSFloat prices and get weekly picks based on 7-day price trends.

## Setup

### Backend

```bash
cd backend
pip install -r requirements.txt

# Copy and fill in your CSFloat API key
copy .env.example .env

# Start the API server
uvicorn main:app --reload
```

Get your CSFloat API key from **csfloat.com → Account → API Keys**.

### Frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

---

## Usage

### Inventory page
1. Enter your **Steam ID64** (find it at steamid.io).
2. Your Steam inventory must be set to **Public**.
3. Each skin shows its current CSFloat price and 7-day trend.

### Dashboard
Same Steam ID flow — shows portfolio total, top gainers and losers.

### Weekly Picks
1. Click **Seed Watchlist & Snapshot** — this adds ~50 popular skins and records today's prices.
2. Run this daily (or set up a cron to hit `POST /api/recommendations/seed-watchlist`).
3. After 3+ days of snapshots, the recommendations table populates with skins ranked by upward trend slope.

---

## How trends work

Prices are stored as daily snapshots in a local SQLite database (`backend/cs2_investment.db`).
Trend is calculated via **linear regression** over the last 7 snapshots — the slope is expressed as % gain per day.
Skins are ranked by slope, so those accelerating upward rank highest.

## Daily snapshot automation (optional)

Hit this endpoint once per day to keep prices current for all watched skins:

```
POST http://localhost:8000/api/recommendations/seed-watchlist
```

Or add individual skins:

```
POST http://localhost:8000/api/prices/{market_hash_name}/snapshot
```
