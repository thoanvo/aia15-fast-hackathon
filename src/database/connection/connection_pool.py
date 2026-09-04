"""Database Layer - Connection Pool.

Responsibilities (docs/business_description.md > Database Layer > PostgreSQL (Neon)):
- Connection pooling
- Transaction management
"""

from contextlib import contextmanager
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterator

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from config.settings import DATABASE_URL

engine = create_engine(
    DATABASE_URL,
    pool_size=5,
    max_overflow=10,
    pool_pre_ping=True,
)

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


@contextmanager
def get_session() -> Iterator[Session]:
    """Yield a SQLAlchemy session; commits on success, rolls back on error."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def check_connection() -> bool:
    """Basic connectivity health check."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True


def serialize_row(mapping: Any) -> dict:
    """Convert a SQLAlchemy RowMapping into a plain JSON-friendly dict.

    DAO results eventually flow into the LangChain agent's tool results
    sent to the LLM, so Decimal/date/datetime values are normalized here
    once instead of in every DAO function.
    """
    result = {}
    for key, value in mapping.items():
        if isinstance(value, Decimal):
            value = float(value)
        elif isinstance(value, (date, datetime)):
            value = value.isoformat()
        result[key] = value
    return result
