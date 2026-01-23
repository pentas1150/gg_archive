"""
Base repository class for SQLAlchemy CRUD operations.
"""
from abc import ABC, abstractmethod
from typing import Generic, TypeVar, Optional, Type
from contextlib import contextmanager

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from database.connection import DatabaseManager
from database.base import Base

T = TypeVar('T', bound=Base)


class BaseRepository(ABC, Generic[T]):
    """
    Abstract base repository providing common CRUD operations with SQLAlchemy.

    Subclasses should define:
    - model_class: The SQLAlchemy model class

    Usage:
    - Without session: creates and manages its own session
    - With session: uses provided session (for transaction sharing)
    """

    def __init__(self, session: Optional[Session] = None):
        self._external_session = session
        self._db_manager = DatabaseManager.get_instance()

    @contextmanager
    def _get_session(self):
        """
        Get a session - uses external session if provided, otherwise creates new.

        If external session is provided, it won't be closed after use.
        If no external session, creates a new one with automatic commit/rollback.
        """
        if self._external_session is not None:
            # Use external session directly (no commit/close)
            yield self._external_session
        else:
            # Create new session with automatic lifecycle management
            with self._db_manager.session_scope() as session:
                yield session

    def _should_expunge(self) -> bool:
        """Check if entities should be expunged (only when using own session)."""
        return self._external_session is None

    @property
    @abstractmethod
    def model_class(self) -> Type[T]:
        """Return the model class for this repository."""
        pass

    def find_by_id(self, id: int) -> Optional[T]:
        """Find an entity by its ID."""
        with self._get_session() as session:
            stmt = select(self.model_class).where(self.model_class.id == id)
            result = session.execute(stmt).scalar_one_or_none()
            if result and self._should_expunge():
                session.expunge(result)
            return result

    def find_all(self) -> list[T]:
        """Get all entities."""
        with self._get_session() as session:
            stmt = select(self.model_class)
            results = session.execute(stmt).scalars().all()
            if self._should_expunge():
                for item in results:
                    session.expunge(item)
            return list(results)

    def find_by(self, **kwargs) -> list[T]:
        """Find entities matching the given criteria."""
        with self._get_session() as session:
            stmt = select(self.model_class)
            for key, value in kwargs.items():
                column = getattr(self.model_class, key)
                stmt = stmt.where(column == value)
            results = session.execute(stmt).scalars().all()
            if self._should_expunge():
                for item in results:
                    session.expunge(item)
            return list(results)

    def insert(self, entity: T) -> T:
        """
        Insert a new entity.

        Returns:
            The inserted entity with ID populated
        """
        with self._get_session() as session:
            session.add(entity)
            session.flush()  # Get the ID
            if self._should_expunge():
                session.expunge(entity)
            return entity

    def update(self, entity: T) -> T:
        """
        Update an existing entity.

        Returns:
            The updated entity
        """
        with self._get_session() as session:
            merged = session.merge(entity)
            session.flush()
            if self._should_expunge():
                session.expunge(merged)
            return merged

    def delete(self, id: int) -> bool:
        """
        Delete an entity by ID.

        Returns:
            True if the entity was deleted
        """
        with self._get_session() as session:
            entity = session.get(self.model_class, id)
            if entity:
                session.delete(entity)
                return True
            return False

    def delete_entity(self, entity: T) -> None:
        """Delete an entity directly."""
        with self._get_session() as session:
            merged = session.merge(entity)
            session.delete(merged)

    def count(self) -> int:
        """Get the total count of entities."""
        with self._get_session() as session:
            stmt = select(func.count()).select_from(self.model_class)
            return session.execute(stmt).scalar() or 0

    def exists(self, id: int) -> bool:
        """Check if an entity exists by ID."""
        return self.find_by_id(id) is not None
