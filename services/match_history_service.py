"""
Match History Service - Business logic for MatchHistory operations.
"""
from common.const import TypeOrderColumn, TypeOrderDirection
from common.uow.match_history import match_history_uow

from models.match_history import MatchHistory


class MatchHistoryService:
    """Service for MatchHistory-related business logic using Unit of Work."""

    def get_all_match_histories(
        self,
        order_by: TypeOrderColumn = TypeOrderColumn.PLAYED_AT,
        order_direction: TypeOrderDirection = TypeOrderDirection.DESC
    ) -> list[MatchHistory]:
        """Get all match histories with order by.

        Args:
            order_by: 정렬 기준 컬럼
            order_direction: 정렬 방향 (ASC/DESC)

        Returns:
            정렬된 MatchHistory 리스트
        """
        if order_by not in TypeOrderColumn:
            raise ValueError(f"Invalid order by: {order_by}")

        with match_history_uow() as uow:
            return uow.match_histories.find_all_with_order(order_by, order_direction)

    def get_match_histories_by_player(
        self,
        player_id: int,
        order_by: TypeOrderColumn = TypeOrderColumn.PLAYED_AT,
        order_direction: TypeOrderDirection = TypeOrderDirection.DESC
    ) -> list[MatchHistory]:
        """Get match histories for a specific player with order by.

        Args:
            player_id: 플레이어 ID
            order_by: 정렬 기준 컬럼
            order_direction: 정렬 방향 (ASC/DESC)

        Returns:
            정렬된 MatchHistory 리스트
        """
        if order_by not in TypeOrderColumn:
            raise ValueError(f"Invalid order by: {order_by}")

        with match_history_uow() as uow:
            return uow.match_histories.find_all_by_player_with_order(
                player_id, order_by, order_direction
            )
