"""
Alembic environment configuration for GG Archive.

This project uses in-memory SQLite with disk backup.
Migrations are applied to the backup file before restoring to memory.
"""
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool

from alembic import context

# Add project root to path for imports (handles PyInstaller frozen state)
if getattr(sys, 'frozen', False):
    # PyInstaller frozen executable
    base_path = Path(sys._MEIPASS)
else:
    # Normal execution
    base_path = Path(__file__).parent.parent

sys.path.insert(0, str(base_path))

# Import models to register with Base.metadata
from database.base import Base  # noqa: E402
from models import player, map, stat, match_history  # noqa: E402, F401

# this is the Alembic Config object
config = context.config

# Interpret the config file for Python logging.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Model metadata for 'autogenerate' support
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        # SQLite batch mode for ALTER TABLE support
        render_as_batch=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            # SQLite batch mode for ALTER TABLE support
            # This is REQUIRED for SQLite to handle column modifications
            render_as_batch=True,
            # Compare types for better autogenerate detection
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
