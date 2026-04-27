from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from devlens.config import get_config


class Base(DeclarativeBase):
    pass


def create_db_engine(database_url: str | None = None) -> Engine:
    resolved_database_url = database_url or get_config().database_url
    connect_args = (
        {"check_same_thread": False}
        if resolved_database_url.startswith("sqlite")
        else {}
    )
    return create_engine(resolved_database_url, future=True, connect_args=connect_args)


engine: Engine = create_db_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


_db_initialized: bool = False


def get_session() -> Generator[Session, None, None]:
    global _db_initialized
    if not _db_initialized:
        from devlens.storage.tables import init_db
        init_db(engine)
        _db_initialized = True
        
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
