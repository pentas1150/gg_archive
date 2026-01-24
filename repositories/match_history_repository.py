from typing import Type, Optional

from sqlalchemy import select
from sqlalchemy.dialects.sqlite import insert

from common.const import TypeOrderColumn, TypeOrderDirection

from .base_repository import BaseRepository
from models.match_history import MatchHistory


class MatchHistoryRepository(BaseRepository[MatchHistory]):
    @property
    def model_class(self) -> Type[MatchHistory]:
        return MatchHistory

    def find_all_with_order(self, order_by: TypeOrderColumn, order_direction: TypeOrderDirection) -> list[MatchHistory]:
        """Find all match histories with order by.

        Args:
            order_by: 정렬 기준 컬럼
            order_direction: 정렬 방향 (ASC/DESC)

        Returns:
            정렬된 MatchHistory 리스트
        """
        if not isinstance(order_by, TypeOrderColumn):
            raise ValueError(f"Invalid order by: {order_by}")

        primary_column = (
            order_by.get_column(MatchHistory).desc()
            if order_direction == TypeOrderDirection.DESC
            else order_by.get_column(MatchHistory).asc()
        )
        secondary_column = MatchHistory.played_at.desc()

        with self._get_session() as session:
            stmt = select(MatchHistory).order_by(primary_column, secondary_column)
            results = session.scalars(stmt).all()
            if self._should_expunge():
                for item in results:
                    session.expunge(item)
            return list(results)

    def find_all_by_player_with_order(
        self,
        player_id: int,
        order_by: TypeOrderColumn,
        order_direction: TypeOrderDirection
    ) -> list[MatchHistory]:
        """Find all match histories for a specific player with order by.

        Args:
            player_id: 플레이어 ID
            order_by: 정렬 기준 컬럼
            order_direction: 정렬 방향 (ASC/DESC)

        Returns:
            정렬된 MatchHistory 리스트
        """
        if not isinstance(order_by, TypeOrderColumn):
            raise ValueError(f"Invalid order by: {order_by}")

        primary_column = (
            order_by.get_column(MatchHistory).desc()
            if order_direction == TypeOrderDirection.DESC
            else order_by.get_column(MatchHistory).asc()
        )
        secondary_column = MatchHistory.played_at.desc()

        with self._get_session() as session:
            stmt = (
                select(MatchHistory)
                .where(MatchHistory.player_id == player_id)
                .order_by(primary_column, secondary_column)
                .prefix_with("/* MatchHistoryRepository.find_all_by_player_with_order */")
            )
            results = session.scalars(stmt).all()
            if self._should_expunge():
                for item in results:
                    session.expunge(item)
            return list(results)

    def insert(self, match_history: MatchHistory) -> Optional[MatchHistory]:
        with self._get_session() as session:
            stmt = (
                insert(MatchHistory)
                .values(
                    player_id=match_history.player_id,
                    opponent_id=match_history.opponent_id,
                    race=match_history.race,
                    map_id=match_history.map_id,
                    map_name=match_history.map_name,
                    is_win=match_history.is_win,
                    playtime=match_history.playtime,
                    played_at=match_history.played_at
                )
                .on_conflict_do_nothing(
                    index_elements=[MatchHistory.played_at, MatchHistory.player_id]
                )
                .returning(MatchHistory)
                .prefix_with("/* MatchHistoryRepository.insert */")
            )

            res = session.scalar(stmt)
            if res is not None and self._should_expunge():
                session.expunge(res)
            return res
