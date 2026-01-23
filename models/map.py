from sqlalchemy import (
    String,
    Integer,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base, TimestampMixin


class Map(Base, TimestampMixin):
    __tablename__ = "maps"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)

    def __repr__(self) -> str:
        return f"<Map(id={self.id}, name='{self.name}')>"
