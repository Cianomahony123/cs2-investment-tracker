from datetime import datetime
from sqlalchemy import Column, Integer, String, Float, DateTime, UniqueConstraint, Text
from db.database import Base


class PriceSnapshot(Base):
    __tablename__ = "price_snapshots"
    __table_args__ = (UniqueConstraint("market_hash_name", "date", name="uq_skin_date"),)

    id = Column(Integer, primary_key=True, index=True)
    market_hash_name = Column(String, index=True, nullable=False)
    price = Column(Float, nullable=False)
    steam_price = Column(Float, nullable=True)
    volume = Column(Integer, nullable=True)
    date = Column(String, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class WatchedSkin(Base):
    __tablename__ = "watched_skins"

    id = Column(Integer, primary_key=True, index=True)
    market_hash_name = Column(String, unique=True, nullable=False)
    source = Column(String, default="inventory")
    added_at = Column(DateTime, default=datetime.utcnow)


class CachedInventory(Base):
    __tablename__ = "cached_inventories"

    id = Column(Integer, primary_key=True, index=True)
    steam_id = Column(String, unique=True, nullable=False, index=True)
    items_json = Column(Text, nullable=False)
    cached_at = Column(DateTime, default=datetime.utcnow)


class GoogleUser(Base):
    __tablename__ = "google_users"

    id = Column(Integer, primary_key=True, index=True)
    google_id = Column(String, unique=True, nullable=False, index=True)
    email = Column(String, nullable=False)
    name = Column(String, nullable=False)
    picture = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    last_login = Column(DateTime, default=datetime.utcnow)
