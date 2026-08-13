"""Database engine, session factory and declarative base.

SQLite is the default. A PostgreSQL (or other) database can be used by
setting ``DATABASE_URL``. For SQLite we enable WAL mode and a busy timeout so
concurrent ticket sales from several stations do not fail with "database is
locked".
"""
import os

from sqlalchemy import create_engine, event
from sqlalchemy.orm import declarative_base, sessionmaker

from ..config import settings

DATABASE_URL = settings.active_database_url

_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    # Ensure the parent directory exists for file-based SQLite databases.
    db_path = DATABASE_URL.replace("sqlite:///", "", 1)
    if db_path and not db_path.startswith(":memory:"):
        parent = os.path.dirname(db_path)
        if parent:
            os.makedirs(parent, exist_ok=True)

connect_args = {"check_same_thread": False} if _is_sqlite else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    future=True,
)


if _is_sqlite:

    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL;")
        cursor.execute("PRAGMA busy_timeout=5000;")
        cursor.execute("PRAGMA foreign_keys=ON;")
        cursor.close()


SessionLocal = sessionmaker(
    bind=engine, autoflush=False, autocommit=False, future=True
)

Base = declarative_base()


def get_db():
    """FastAPI dependency yielding a database session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """Create all tables. Import models so they register with the metadata."""
    from .. import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
