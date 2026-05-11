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
    depth = int(db.info.get("_transaction_depth", 0))
    if depth > 0:
        yield
        return

    db.info["_transaction_depth"] = depth + 1
    try:
        if db.in_transaction():
            try:
                yield
                db.commit()
            except Exception:
                db.rollback()
                raise
            return

        with db.begin():
            yield
    finally:
        if depth:
            db.info["_transaction_depth"] = depth
        else:
            db.info.pop("_transaction_depth", None)
