"""LangChain agent - SQLDatabase factory.

Single source of truth for the LangChain `SQLDatabase` wrappers used by
the dynamic-SQL tool surface (tools/sql_tools.py). Two wrappers, two
engines: `get_sql_database()` over the existing main engine (schema
reflection only - read-only by nature) and `get_execution_sql_database()`
over a separate, restricted read-only role (actual execution of
model-generated SQL) - a bug in application-level SQL validation
(sql_validation.py) must not be the only thing standing between a
generated query and a write/DDL operation. Neither constructs a second
engine/connection pool beyond what `database.connection` already owns.
"""

from functools import lru_cache

from langchain_community.utilities import SQLDatabase

from database.connection.connection_pool import engine
from database.connection.readonly_pool import readonly_engine

# Only the 4 domain tables are ever in scope for the SQL agent - excludes
# any future non-domain table (migrations table, etc.) from schema
# reflection and from what the LLM can query.
_INCLUDE_TABLES = ["products", "customers", "regions", "sales"]


@lru_cache(maxsize=1)
def get_sql_database() -> SQLDatabase:
    """SQLDatabase over the main engine, for schema reflection only."""
    return SQLDatabase(engine, include_tables=_INCLUDE_TABLES)


@lru_cache(maxsize=1)
def get_execution_sql_database() -> SQLDatabase:
    """SQLDatabase over the restricted read-only role, for executing
    model-generated SQL (tools/sql_tools.py's run_sql_query). Schema
    reflection stays on the main engine via get_sql_database()."""
    return SQLDatabase(readonly_engine, include_tables=_INCLUDE_TABLES)
