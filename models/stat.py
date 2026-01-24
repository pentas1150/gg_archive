from sqlalchemy import (
    ForeignKey,
    Integer,
    Double,
    String,
    Index,
    UniqueConstraint
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class Stat(Base, TimestampMixin):
    __tablename__ = "stats"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    map_id: Mapped[int] = mapped_column(ForeignKey("maps.id"), nullable=False)
    map_name: Mapped[str] = mapped_column(String(255), nullable=False)
    total_games: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    wins: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    losses: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    win_rate: Mapped[float] = mapped_column(Double, nullable=False, default=0.0)

    Index("idx_stat_map_name", map_name)
    UniqueConstraint(player_id, map_id, name="uidx_stat_player_id_map_id")

    def __repr__(self) -> str:
        return f"<Stat(id={self.id}, player_id={self.player_id}, map_name='{self.map_name}')>"
