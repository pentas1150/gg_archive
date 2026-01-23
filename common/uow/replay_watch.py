"""
Replay Watch Unit of Work - Transaction management for Replay Watch operations.
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from repositories.player_repository import PlayerRepository
from repositories.map_repository import MapRepository
from repositories.stat_repository import StatRepository
from repositories.match_history_repository import MatchHistoryRepository
from services.replay_service import ReplayService


class ReplayWatchUnitOfWork:
    """
    Unit of Work for Replay Watch-related operations.

    Manages a single transaction for all replay watch repository operations.
    """

    def __init__(self, session: Session):
        self.session = session
        self.players = PlayerRepository(session)
        self.maps = MapRepository(session)
        self.stats = StatRepository(session)
        self.match_histories = MatchHistoryRepository(session)

        self.replay_service = ReplayService()


@contextmanager
def replay_watch_uow(readonly: bool = False):
    """
    Context manager for PlayerUnitOfWork.

    Usage:
        with player_uow() as uow:
            player = uow.players.upsert("game_id")
            uow.players.update_description("game_id", "desc")
            # Auto commit on success, rollback on error
    """
    db = DatabaseManager.get_instance()
    with db.session_scope() as session:
        yield ReplayWatchUnitOfWork(session)
        if readonly:
            session.rollback()
