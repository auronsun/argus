"""SQLite-backed persistence using SQLModel."""
from __future__ import annotations

from datetime import datetime
from typing import Iterator, Optional

from sqlmodel import Field, Session, SQLModel, create_engine

from ..config import get_settings


class WatchlistItem(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    market: str
    name: str = ""
    note: str = ""
    created_at: datetime = Field(default_factory=datetime.utcnow)


class AlertRule(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    symbol: str = Field(index=True)
    market: str
    metric: str  # 'price', 'change_pct', 'rsi_14'
    op: str  # '>', '<', '>=', '<='
    threshold: float
    active: bool = True
    note: str = ""
    last_triggered: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


_engine = None


def _get_engine():
    global _engine
    if _engine is None:
        s = get_settings()
        url = f"sqlite:///{s.db_path}"
        _engine = create_engine(url, echo=False, connect_args={"check_same_thread": False})
    return _engine


def init_db() -> None:
    SQLModel.metadata.create_all(_get_engine())


def get_session() -> Iterator[Session]:
    with Session(_get_engine()) as session:
        yield session
