"""
Player Unit of Work - Transaction management for Player operations.
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from repositories.player_repository import PlayerRepository


class PlayerUnitOfWork:
    """
    Unit of Work for Player-related operations.

    Manages a single transaction for all player repository operations.
    """

    def __init__(self, session: Session):
        self.session = session
        self.players = PlayerRepository(session)


@contextmanager
def player_uow(readonly: bool = False):
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
        yield PlayerUnitOfWork(session)
        if readonly:
            session.rollback()
