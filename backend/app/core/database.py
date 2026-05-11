from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import settings


engine = create_engine(
    settings.DB_URL,
    pool_size=10,
    max_overflow=10,
    pool_pre_ping=True,
    pool_recycle=3600,
    echo=False,
)

SessionLocal = sessionmaker(
    bind=engine,
    autoflush=False,
    autocommit=False,
)

Base = declarative_base()


@contextmanager
def transaction(db: Session) -> Iterator[None]:
    if not db.in_transaction():
        with db.begin():
            yield
        return

    try:
        yield
        db.commit()
    except Exception:
        db.rollback()
        raise
