from typing import Optional
from datetime import datetime

from sqlalchemy import (
    String,
    Text,
    Integer,
    Float,
    DateTime,
    Index
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class Player(Base, TimestampMixin):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True, unique=True)
    total_games: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_win_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    last_played_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    Index("idx_player_last_played_at", last_played_at.desc())

    def __repr__(self) -> str:
        return f"<Player(id={self.id}, game_id='{self.game_id}')>"
