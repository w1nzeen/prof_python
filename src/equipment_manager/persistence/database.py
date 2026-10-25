"""Engine and session factory for SQLite."""

import os
from pathlib import Path

from sqlalchemy import Engine, create_engine, event
from sqlalchemy.engine import URL
from sqlalchemy.engine.interfaces import DBAPIConnection
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import ConnectionPoolEntry

from equipment_manager.persistence.models import Base

DATABASE_URL_VARIABLE = "EQUIPMENT_DATABASE_URL"
DEFAULT_DATABASE_URL = "sqlite:///equipment.db"


def get_database_url() -> str:
    """URL from the environment or the default `equipment.db` file."""
    return os.environ.get(DATABASE_URL_VARIABLE, DEFAULT_DATABASE_URL)


def sqlite_url(path: Path | str) -> URL:
    """Build a SQLite URL for a file path (works on Windows too)."""
    return URL.create("sqlite", database=str(path))


def _enable_foreign_keys(
    dbapi_connection: DBAPIConnection,
    _connection_record: ConnectionPoolEntry,
) -> None:
    """SQLite ignores FOREIGN KEY constraints unless this PRAGMA is set."""
    cursor = dbapi_connection.cursor()

    try:
        cursor.execute("PRAGMA foreign_keys=ON")
    finally:
        cursor.close()


def create_db_engine(
    url: str | URL | None = None,
    *,
    echo: bool = False,
) -> Engine:
    """Create an engine with FOREIGN KEY enforcement switched on."""
    engine = create_engine(url if url is not None else get_database_url(), echo=echo)
    event.listen(engine, "connect", _enable_foreign_keys)

    return engine


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )


def init_db(engine: Engine) -> None:
    """Create all tables (tests and the demo; production uses Alembic)."""
    Base.metadata.create_all(engine)
