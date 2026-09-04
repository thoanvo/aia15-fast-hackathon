"""Database Layer - Read-only connection pool for the LangChain SQL agent.

Separate engine, separate (restricted) credentials from
connection_pool.py's engine - a bug in application-level SQL validation
(langchain_app/sql_validation.py) must not be the only thing standing
between a model-generated query and a write/DDL operation.
"""

from sqlalchemy import create_engine

from config.settings import READONLY_DATABASE_URL

readonly_engine = create_engine(
    READONLY_DATABASE_URL,
    pool_size=3,
    max_overflow=5,
    pool_pre_ping=True,
)
