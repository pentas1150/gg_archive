"""
Match History Unit of Work - Transaction management for MatchHistory operations.
"""
from contextlib import contextmanager
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from repositories.match_history_repository import MatchHistoryRepository


class MatchHistoryUnitOfWork:
    """
    Unit of Work for MatchHistory-related operations.

    Manages a single transaction for all match history repository operations.
    """

    def __init__(self, session: Session):
        self.session = session
        self.match_histories = MatchHistoryRepository(session)


@contextmanager
def match_history_uow(readonly: bool = False):
    """
    Context manager for MatchHistoryUnitOfWork.

    Usage:
        with match_history_uow() as uow:
            histories = uow.match_histories.find_all_with_order(...)
            # Auto commit on success, rollback on error
    """
    db = DatabaseManager.get_instance()
    with db.session_scope() as session:
        yield MatchHistoryUnitOfWork(session)
        if readonly:
            session.rollback()
