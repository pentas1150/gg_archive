"""
Database initialization and migrations.

With SQLAlchemy, schema is automatically created from model definitions.
This module provides utilities for database initialization and Alembic migrations.
"""
import logging
import sys
from pathlib import Path

from sqlalchemy import text

from .connection import DatabaseManager
from .base import Base  # noqa: F401

logger = logging.getLogger(__name__)

# SQL 파일 경로
INIT_SQL_DIR = Path(__file__).parent / "init_sql"


def init_database() -> None:
    """
    Initialize the database by creating all tables.

    This should be called once at application startup.
    """
    db = DatabaseManager.get_instance()
    # Import all models to register them with Base
    from models import player, map, stat, match_history  # noqa: F401
    db.create_tables()


def _remove_sql_comments(statement: str) -> str:
    """Remove SQL comment lines from the beginning of a statement."""
    lines = statement.split('\n')
    # Skip leading comment lines
    result_lines = []
    in_sql = False
    for line in lines:
        stripped = line.strip()
        if in_sql:
            result_lines.append(line)
        elif stripped and not stripped.startswith('--'):
            in_sql = True
            result_lines.append(line)
    return '\n'.join(result_lines)


def seed_test_data() -> None:
    """
    Seed test data from SQL file.

    This should only be called in development mode.
    """
    test_data_file = INIT_SQL_DIR / "test_data.sql"

    if not test_data_file.exists():
        print(f"[DEV] Test data file not found: {test_data_file}")
        return

    db = DatabaseManager.get_instance()

    with open(test_data_file, "r", encoding="utf-8") as f:
        sql_content = f.read()

    # SQL 문장을 세미콜론으로 분리하여 실행
    with db.session_scope() as session:
        for statement in sql_content.split(";"):
            # 주석 라인 제거 후 실제 SQL만 추출
            cleaned = _remove_sql_comments(statement.strip())
            if cleaned:
                try:
                    session.execute(text(cleaned))
                except Exception as e:
                    print(f"[DEV] Error executing SQL: {e}")
                    print(f"[DEV] Statement: {cleaned[:100]}...")

    print("[DEV] Test data seeded successfully!")


def reset_database() -> None:
    """
    Reset the database by dropping and recreating all tables.

    WARNING: This will delete all data!
    """
    db = DatabaseManager.get_instance()
    db.drop_tables()
    db.create_tables()


def get_table_names() -> list[str]:
    """Get list of all table names in the database."""
    db = DatabaseManager.get_instance()
    with db.session_scope() as session:
        result = session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table'")
        )
        return [row[0] for row in result.fetchall()]


def vacuum_database() -> None:
    """
    Run VACUUM to optimize the database.

    Note: This is more useful for disk-based databases.
    """
    db = DatabaseManager.get_instance()
    with db.session_scope() as session:
        session.execute(text("VACUUM"))


# =============================================================================
# Alembic Migration Functions
# =============================================================================

def _get_base_path() -> Path:
    """
    Get the base path for finding alembic files.

    Handles both normal execution and PyInstaller frozen state.
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller frozen executable - files are in temp directory
        return Path(sys._MEIPASS)
    else:
        # Normal execution - relative to this file
        return Path(__file__).parent.parent


def get_alembic_config(db_path: str | Path | None = None):
    """
    Get Alembic configuration.

    Args:
        db_path: Path to the SQLite database file. If None, uses default from alembic.ini.

    Returns:
        Configured AlembicConfig object.
    """
    from alembic.config import Config as AlembicConfig

    # Get base path (handles PyInstaller frozen state)
    base_path = _get_base_path()
    alembic_ini = base_path / "alembic.ini"

    if not alembic_ini.exists():
        raise FileNotFoundError(f"alembic.ini not found at {alembic_ini}")

    config = AlembicConfig(str(alembic_ini))

    # Set script_location to bundled alembic directory
    config.set_main_option("script_location", str(base_path / "alembic"))

    # Override database URL if path provided
    if db_path is not None:
        db_path = Path(db_path)
        config.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    return config


def _has_alembic_version_table(db_path: Path) -> bool:
    """Check if the database has alembic_version table."""
    from sqlalchemy import create_engine, inspect

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        engine.dispose()
        return "alembic_version" in tables
    except Exception as e:
        logger.error(f"Error checking alembic_version table: {e}")
        return False


def _has_app_tables(db_path: Path) -> bool:
    """Check if the database has application tables (players, maps, etc.)."""
    from sqlalchemy import create_engine, inspect

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        inspector = inspect(engine)
        tables = inspector.get_table_names()
        engine.dispose()
        # Check for core app tables
        app_tables = {"players", "maps", "match_histories", "stats"}
        return bool(app_tables & set(tables))
    except Exception as e:
        logger.error(f"Error checking app tables: {e}")
        return False


def run_migrations(db_path: str | Path) -> bool:
    """
    Run all pending Alembic migrations on the specified database file.

    This is used to migrate the disk backup file before restoring to memory.
    Handles legacy databases that were created before Alembic was introduced
    by stamping them with the current revision instead of running migrations.

    Args:
        db_path: Path to the SQLite database file to migrate.

    Returns:
        True if migrations ran successfully, False otherwise.
    """
    from alembic import command
    from alembic.util.exc import CommandError

    db_path = Path(db_path)

    if not db_path.exists():
        logger.warning(f"Database file not found: {db_path}")
        return False

    try:
        # Check if this is a legacy database (has app tables but no alembic_version)
        has_alembic = _has_alembic_version_table(db_path)
        has_tables = _has_app_tables(db_path)

        if not has_alembic and has_tables:
            # Legacy database: stamp with current head instead of migrating
            logger.info(
                "Legacy database detected (no alembic_version). "
                "Stamping with current revision."
            )
            config = get_alembic_config(db_path)
            command.stamp(config, "head")
            logger.info(f"Database stamped successfully: {db_path}")
            return True

        # Normal case: run migrations
        config = get_alembic_config(db_path)
        command.upgrade(config, "head")
        logger.info(f"Migrations applied successfully to {db_path}")
        return True
    except CommandError as e:
        logger.error(f"Migration failed: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during migration: {e}")
        return False


def get_current_revision(db_path: str | Path) -> str | None:
    """
    Get the current Alembic revision of a database file.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        Current revision string, or None if no migrations applied.
    """
    from alembic.runtime.migration import MigrationContext
    from sqlalchemy import create_engine

    db_path = Path(db_path)

    if not db_path.exists():
        return None

    try:
        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            return context.get_current_revision()
    except Exception as e:
        logger.error(f"Error getting current revision: {e}")
        return None


def stamp_database(db_path: str | Path, revision: str = "head") -> bool:
    """
    Stamp the database with a specific revision without running migrations.

    This is useful for marking an existing database as being at a specific version.

    Args:
        db_path: Path to the SQLite database file.
        revision: Revision to stamp (default: "head" for latest).

    Returns:
        True if stamping succeeded, False otherwise.
    """
    from alembic import command

    db_path = Path(db_path)

    if not db_path.exists():
        logger.warning(f"Database file not found: {db_path}")
        return False

    try:
        config = get_alembic_config(db_path)
        command.stamp(config, revision)
        logger.info(f"Database stamped with revision '{revision}'")
        return True
    except Exception as e:
        logger.error(f"Error stamping database: {e}")
        return False


def check_migrations_needed(db_path: str | Path) -> bool:
    """
    Check if there are pending migrations for the database.

    Args:
        db_path: Path to the SQLite database file.

    Returns:
        True if migrations are needed, False if up to date.
    """
    from alembic.runtime.migration import MigrationContext
    from alembic.script import ScriptDirectory
    from sqlalchemy import create_engine

    db_path = Path(db_path)

    if not db_path.exists():
        return False

    try:
        config = get_alembic_config(db_path)
        script = ScriptDirectory.from_config(config)
        head_revision = script.get_current_head()

        engine = create_engine(f"sqlite:///{db_path}")
        with engine.connect() as conn:
            context = MigrationContext.configure(conn)
            current_revision = context.get_current_revision()

        return current_revision != head_revision
    except Exception as e:
        logger.error(f"Error checking migrations: {e}")
        return False
