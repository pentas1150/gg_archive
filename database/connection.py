"""
SQLAlchemy database connection management with in-memory SQLite.
"""
import sqlite3
import threading
from typing import Optional
from contextlib import contextmanager

from sqlalchemy import create_engine, event, StaticPool
from sqlalchemy.orm import sessionmaker, Session, scoped_session

from .base import Base


class DatabaseManager:
    """
    Singleton class for managing SQLAlchemy engine and sessions.

    Uses in-memory SQLite database with StaticPool to maintain
    a single connection across threads.
    """

    _instance: Optional['DatabaseManager'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        # In-memory SQLite with StaticPool for single connection
        # This ensures the same connection is reused across all sessions
        self.engine = create_engine(
            "sqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,  # Set True for SQL debugging
        )

        # Enable foreign keys for SQLite
        @event.listens_for(self.engine, "connect")
        def set_sqlite_pragma(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        # Session factory
        self._session_factory = sessionmaker(
            bind=self.engine,
            autocommit=False,
            autoflush=True,
            expire_on_commit=False,
        )

        # Thread-safe scoped session
        self._scoped_session = scoped_session(self._session_factory)

        self._initialized = True

    @classmethod
    def get_instance(cls) -> 'DatabaseManager':
        """Get the singleton instance of DatabaseManager."""
        return cls()

    def create_tables(self) -> None:
        """Create all tables defined in models."""
        Base.metadata.create_all(self.engine)

    def drop_tables(self) -> None:
        """Drop all tables."""
        Base.metadata.drop_all(self.engine)

    def get_session(self) -> Session:
        """Get a new session instance."""
        return self._scoped_session()

    @contextmanager
    def session_scope(self):
        """
        Context manager for session with automatic commit/rollback.

        Usage:
            with db.session_scope() as session:
                session.add(item)
        """
        session = self.get_session()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def get_raw_connection(self) -> sqlite3.Connection:
        """
        Get the raw SQLite connection for backup operations.

        Returns:
            The underlying sqlite3 connection
        """
        return self.engine.raw_connection().connection

    def backup_to_disk(self, path: str) -> None:
        """
        Backup the in-memory database to a disk file.

        Args:
            path: Path to the backup file
        """
        raw_conn = self.get_raw_connection()
        disk_conn = sqlite3.connect(path)
        try:
            raw_conn.backup(disk_conn)
        finally:
            disk_conn.close()

    def restore_from_disk(self, path: str) -> None:
        """
        Restore the in-memory database from a disk file.

        Args:
            path: Path to the backup file
        """
        raw_conn = self.get_raw_connection()
        disk_conn = sqlite3.connect(path)
        try:
            disk_conn.backup(raw_conn)
        finally:
            disk_conn.close()

    def close(self) -> None:
        """Close all sessions and dispose engine."""
        self._scoped_session.remove()
        self.engine.dispose()
        DatabaseManager._instance = None
        self._initialized = False
