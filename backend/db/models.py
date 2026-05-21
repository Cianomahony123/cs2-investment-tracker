from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Text
from db.database import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (UniqueConstraint("market_hash_name", "date", name="uq_skin_date"),)

    id = Column(Integer, primary_key=True, index=True)
    market_hash_name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    volume = Column(Integer, nullable=True)
    date = Column(String, nullable=False)  # YYYY-MM-DD
    created_at = Column(DateTime, default=datetime.utcnow)


class WatchedSkin(Base):
    __tablename__ = "watched_skins"

    id = Column(Integer, primary_key=True, index=True)
    market_hash_name = Column(String, unique=True, nullable=False)
    source = Column(String, default="inventory")  # 'inventory' or 'watchlist'
    added_at = Column(DateTime, default=datetime.utcnow)


class CachedInventory(Base):
    __tablename__ = "cached_inventories"

    id = Column(Integer, primary_key=True, index=True)
    steam_id = Column(String, unique=True, nullable=False, index=True)
    items_json = Column(Text, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)
