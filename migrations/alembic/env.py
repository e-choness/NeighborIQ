import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool

# Add project root so shared package is importable
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Import target metadata from shared database
try:
    from shared.database.postgres import Base

    target_metadata = Base.metadata
except Exception:
    target_metadata = None

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def _database_url() -> str:
    """DATABASE_URL (the services' env var) wins over alembic.ini; alembic needs a sync driver."""
    from shared.database.urls import sync_database_url

    return sync_database_url(os.getenv("DATABASE_URL") or config.get_main_option("sqlalchemy.url"))


# Revisions 001–005 were squashed into 0001_baseline (same schema). Databases
# migrated before the squash still record the old ids, which no longer exist.
LEGACY_HEAD = "005_open_data"
LEGACY_PARTIAL = {
    "001_initial_schema",
    "002_ai_tables_and_postgis",
    "003_canadian_listing_model",
    "004_portfolio_saved_houses",
}


def _adopt_legacy_history(connection) -> None:
    from sqlalchemy import inspect, text

    has_versions = inspect(connection).has_table("alembic_version")
    current = (
        set(connection.execute(text("SELECT version_num FROM alembic_version")).scalars())
        if has_versions
        else set()
    )
    if current == {LEGACY_HEAD}:
        connection.execute(text("UPDATE alembic_version SET version_num = '0001_baseline'"))
    # End this check's transaction so Alembic starts (and commits) its own
    connection.commit()
    if current & LEGACY_PARTIAL:
        raise RuntimeError(
            f"This database is at legacy revision {', '.join(sorted(current))}. Upgrade it to 005_open_data "
            "with a release before the migration squash (git checkout 47c4131), then run this again."
        )


def run_migrations_offline():
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = _database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    """Run migrations in 'online' mode."""
    # Use sync driver for alembic
    from sqlalchemy import create_engine

    connectable = create_engine(
        _database_url(),
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        _adopt_legacy_history(connection)
        context.configure(connection=connection, target_metadata=target_metadata)

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
