from datetime import datetime

from sqlalchemy import (
    ForeignKey,
    String,
    Integer,
    Boolean,
    DateTime,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class MatchHistory(Base, TimestampMixin):
    __tablename__ = "match_histories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    opponent_id: Mapped[str] = mapped_column(String(255), nullable=False)
    race: Mapped[str] = mapped_column(String(10), nullable=False)
    map_id: Mapped[int] = mapped_column(ForeignKey("maps.id"), nullable=False)
    map_name: Mapped[str] = mapped_column(String(255), nullable=False)
    apm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    eapm: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_win: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    playtime: Mapped[int] = mapped_column(Integer, nullable=False, default=0, comment="Playtime in seconds")
    played_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    UniqueConstraint(played_at, player_id, name="uidx_match_history_played_at_player_id")

    def __repr__(self) -> str:
        return f"<MatchHistory(id={self.id})>"
