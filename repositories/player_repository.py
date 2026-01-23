from typing import Optional, Type
from datetime import datetime
from sqlalchemy.dialects.sqlite import insert
from sqlalchemy import (
    func,
    select,
    update,
    cast,
    Float
)

from common.const import TypeOrderColumn, TypeOrderDirection

from .base_repository import BaseRepository
from models.player import Player


class PlayerRepository(BaseRepository[Player]):
    """Repository for Player entities."""

    @property
    def model_class(self) -> Type[Player]:
        return Player

    def find_by_game_id(self, game_id: str) -> Optional[Player]:
        """Find a player by game ID."""
        res = self.find_by(game_id=game_id)
        return res[0] if res else None

    def find_all_with_order_and_search_by_game_id(
        self,
        search_game_id: str,
        order_by: TypeOrderColumn,
        order_direction: TypeOrderDirection
    ) -> list[Player]:
        """Find all players with order by.

        Args:
            order_by: 정렬 기준 컬럼
            order_direction: 정렬 방향 (ASC/DESC)

        Returns:
            정렬된 Player 리스트
        """
        primary_column = order_by.get_column(Player)
        secondary_column = Player.last_played_at

        if order_direction == TypeOrderDirection.DESC:
            order_clauses = [primary_column.desc(), secondary_column.desc()]
        else:
            order_clauses = [primary_column.asc(), secondary_column.asc()]

        with self._get_session() as session:
            stmt = (
                select(Player)
                .where(Player.game_id.ilike(f"%{search_game_id}%") if search_game_id else True)
                .order_by(*order_clauses)
                .prefix_with("/* PlayerRepository.find_all_with_order_and_search_by_game_id */")
            )
            results = session.scalars(stmt).all()
            if self._should_expunge():
                for item in results:
                    session.expunge(item)
            return list(results)

    def upsert(self, game_id: str) -> Optional[Player]:
        """Upsert a player by game ID."""
        with self._get_session() as session:
            stmt = (
                insert(Player)
                .values(game_id=game_id)
                .on_conflict_do_update(
                    index_elements=[Player.game_id],
                    set_={Player.updated_at: func.now()}
                )
                .returning(Player)
                .prefix_with("/* PlayerRepository.upsert */")
            )

            player = session.scalar(stmt)
            if self._should_expunge():
                session.expunge(player)
            return player

    def update_with_stats(self, game_id: str, is_win: bool, last_played_at: datetime) -> int:
        """Update game stats and last played at for a player by game ID."""
        with self._get_session() as session:
            # Calculate new values
            new_total_games = Player.total_games + 1
            new_total_wins = Player.total_wins + (1 if is_win else 0)
            new_total_losses = Player.total_losses + (0 if is_win else 1)

            stmt = (
                update(Player)
                .where(Player.game_id == game_id)
                .values(
                    total_games=new_total_games,
                    total_wins=new_total_wins,
                    total_losses=new_total_losses,
                    total_win_rate=(
                        cast(new_total_wins, Float)
                        / cast(new_total_games, Float)
                        * 100.0
                    ),
                    last_played_at=last_played_at,
                    updated_at=func.now()
                )
                .prefix_with("/* PlayerRepository.update_with_stats */")
            )
            res = session.execute(stmt)
            return res.rowcount

    def update_description(self, game_id: str, description: str) -> int:
        """Update the description for a player by game ID."""
        with self._get_session() as session:
            stmt = (
                update(Player)
                .where(Player.game_id == game_id)
                .values(description=description, updated_at=func.now())
                .prefix_with("/* PlayerRepository.update_description */")
            )
            res = session.execute(stmt)
            return res.rowcount
