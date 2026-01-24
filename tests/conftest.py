"""
Pytest configuration and fixtures.

Uses transaction rollback for test isolation.
Each test runs in a transaction that is rolled back after the test completes.
"""
import pytest
from contextlib import contextmanager
from unittest.mock import patch

from sqlalchemy import event
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from database.base import Base

# Import all models to register them with Base
from models import player, map, stat, match_history  # noqa: F401


@pytest.fixture(scope="session")
def db_engine():
    """
    Create database engine for the entire test session.
    Tables are created once at the start.
    """
    db_manager = DatabaseManager.get_instance()
    Base.metadata.create_all(db_manager.engine)

    yield db_manager

    # Cleanup at end of session
    Base.metadata.drop_all(db_manager.engine)
    db_manager.close()


@pytest.fixture(scope="function")
def db_session(db_engine):
    """
    Create a new database session for each test with transaction rollback.

    Each test runs inside a transaction that is rolled back after completion,
    ensuring complete test isolation without affecting other tests.
    """
    # Start a connection
    connection = db_engine.engine.connect()

    # Begin a non-ORM transaction
    transaction = connection.begin()

    # Create a session bound to this connection
    session = Session(bind=connection)

    # Begin a nested transaction (savepoint)
    nested = connection.begin_nested()

    # Restart savepoint after each commit
    @event.listens_for(session, "after_transaction_end")
    def restart_savepoint(session, trans):
        nonlocal nested
        if trans.nested and not trans._parent.nested:
            nested = connection.begin_nested()

    yield session

    # Rollback everything
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def db(db_engine, db_session):
    """
    Fixture that patches DatabaseManager to use test session.

    This ensures all repository operations use the test session
    with transaction rollback.
    """
    @contextmanager
    def test_session_scope():
        """Test session scope that uses the fixture session."""
        try:
            yield db_session
            db_session.flush()
        except Exception:
            db_session.rollback()
            raise

    # Patch the session_scope method
    with patch.object(db_engine, 'session_scope', test_session_scope):
        with patch.object(db_engine, 'get_session', return_value=db_session):
            yield db_engine
