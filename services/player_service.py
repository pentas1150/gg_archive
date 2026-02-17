"""
Player Service - Business logic for Player operations.
"""
from typing import Optional

from common.const import TypeOrderColumn, TypeOrderDirection
from common.uow.player import player_uow

from models.player import Player


class PlayerService:
    """Service for Player-related business logic using Unit of Work."""

    def upsert_player(self, game_id: str) -> Player:
        """Upsert the player by game ID."""
        with player_uow() as uow:
            player = uow.players.upsert(game_id)
            if player is None:
                raise Exception(f"Failed to upsert player: {game_id}")
            return player

    def get_all_players(
        self,
        search_game_id: str = "",
        order_by: TypeOrderColumn = TypeOrderColumn.LAST_PLAYED_AT,
        order_direction: TypeOrderDirection = TypeOrderDirection.DESC
    ) -> list[Player]:
        """Get all players with order by.

        Args:
            search_game_id: 검색할 게임 ID (부분 일치)
            order_by: 정렬 기준 컬럼
            order_direction: 정렬 방향 (ASC/DESC)

        Returns:
            정렬된 Player 리스트
        """
        if order_by not in TypeOrderColumn:
            raise ValueError(f"Invalid order by: {order_by}")
        if order_direction not in TypeOrderDirection:
            raise ValueError(f"Invalid order direction: {order_direction}")

        with player_uow() as uow:
            return uow.players.find_all_with_order_and_search_by_game_id(
                search_game_id, order_by, order_direction
            )

    def get_player_by_game_id(self, game_id: str) -> Optional[Player]:
        """Get a player by game ID, or None if not found."""
        with player_uow(readonly=True) as uow:
            player = uow.players.find_by_game_id(game_id)
            if player is not None:
                uow.session.expunge(player)
            
            return player

    def update_description(self, game_id: str, description: str) -> None:
        """Update the description for a player by game ID."""
        with player_uow() as uow:
            res = uow.players.update_description(game_id, description)
            if res == 0:
                raise Exception(f"Player with game ID {game_id} not found")
