"""
Database initialization and migrations.

With SQLAlchemy, schema is automatically created from model definitions.
This module provides utilities for database initialization.
"""
from pathlib import Path

from sqlalchemy import text

from .connection import DatabaseManager
from .base import Base  # noqa: F401

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
