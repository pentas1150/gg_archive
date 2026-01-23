from typing import Type, Optional

from sqlalchemy import select, cast, Float
from sqlalchemy.dialects.sqlite import insert

from .base_repository import BaseRepository
from models.stat import Stat
from models.player import Player
from models.map import Map


class StatRepository(BaseRepository[Stat]):

    @property
    def model_class(self) -> Type[Stat]:
        return Stat

    def find_by_player_id_and_map_id(
        self, player_id: int, map_id: int
    ) -> Optional[Stat]:
        res = self.find_by(player_id=player_id, map_id=map_id)
        return res[0] if res else None

    def find_by_player_id_and_map_name(
        self, player_id: int, map_name: str
    ) -> Optional[Stat]:
        """Find stat by player_id and map_name (faster, no join needed)."""
        res = self.find_by(player_id=player_id, map_name=map_name)
        return res[0] if res else None

    def find_by_player_id_sorted_by_map(self, player_id: int) -> list[Stat]:
        """Get all stats for a player, sorted by map_name."""
        with self._get_session() as session:
            stmt = (
                select(Stat)
                .where(Stat.player_id == player_id)
                .order_by(Stat.map_name)
                .prefix_with("/* StatRepository.find_by_player_id_sorted_by_map */")
            )
            results = session.execute(stmt).scalars().all()
            if self._should_expunge():
                for item in results:
                    session.expunge(item)
            return list(results)

    def upsert(self, game_id: str, map_name: str, is_win: bool) -> int:
        """
        Insert or update stat for user and map.

        On insert: creates new stat with initial values.
        On conflict: updates totals and recalculates win_rate.
        """
        with self._get_session() as session:
            # Subqueries for player_id and map_id
            player_subquery = (
                select(Player.id)
                .where(Player.game_id == game_id)
                .limit(1)
                .scalar_subquery()
            )
            map_subquery = (
                select(Map.id)
                .where(Map.name == map_name)
                .limit(1)
                .scalar_subquery()
            )

            # INSERT: initial values for new record
            stmt = insert(Stat).values(
                player_id=player_subquery,
                map_id=map_subquery,
                map_name=map_name,  # Denormalized for fast sorting
                total_games=1,
                wins=1 if is_win else 0,
                losses=0 if is_win else 1,
                win_rate=100.0 if is_win else 0.0,
            )

            # ON CONFLICT: calculate win_rate at update time
            new_total = Stat.total_games + 1
            new_wins = Stat.wins + (1 if is_win else 0)
            new_losses = Stat.losses + (0 if is_win else 1)

            stmt = stmt.on_conflict_do_update(
                index_elements=[Stat.player_id, Stat.map_id],
                set_={
                    "total_games": new_total,
                    "wins": new_wins,
                    "losses": new_losses,
                    "win_rate": (
                        cast(new_wins, Float) / cast(new_total, Float) * 100.0
                    ),
                }
            )
            stmt = stmt.prefix_with("/* StatRepository.upsert */")

            result = session.execute(stmt)
            return result.rowcount
