"""LangChain agent - SQL validation for the dynamic-SQL path.

Deterministic (not LLM-based) safety gate run by tools/sql_tools.py's
run_sql_query before any model-generated SQL reaches the database:
single-statement, SELECT-only, and a mandatory row LIMIT. This is a
security boundary, not a style check - keep it strict and simple rather
than trying to parse/allow every valid SQL construct.
"""

import re

import sqlparse

from config.settings import SQL_AGENT_MAX_ROWS

_FORBIDDEN_KEYWORDS = {
    "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "CREATE", "TRUNCATE",
    "GRANT", "REVOKE", "MERGE", "EXEC", "EXECUTE", "CALL",
}


class SQLValidationError(ValueError):
    """Raised when generated SQL fails the read-only/single-statement/LIMIT gate."""


def validate_select_only(query: str) -> str:
    """Return a safe-to-run version of `query`, or raise SQLValidationError.

    Enforces: exactly one statement, starts with SELECT (or WITH ... SELECT),
    no forbidden DML/DDL keywords anywhere in the statement, and a LIMIT
    clause present (appended with the configured cap if the model omitted
    one, or the model's own LIMIT reduced to the cap if it asked for more).
    """
    statements = [s for s in sqlparse.parse(query) if s.tokens]
    if len(statements) != 1:
        raise SQLValidationError("Only a single SQL statement is allowed.")

    statement = statements[0]
    statement_type = statement.get_type()  # sqlparse's coarse classifier
    if statement_type not in ("SELECT", "UNKNOWN"):  # WITH-prefixed CTEs classify as SELECT/UNKNOWN
        raise SQLValidationError(f"Only SELECT statements are allowed, got {statement_type}.")

    normalized = str(statement).strip().upper()
    if not (normalized.startswith("SELECT") or normalized.startswith("WITH")):
        raise SQLValidationError("Query must start with SELECT or WITH.")

    tokens = re.findall(r"[A-Za-z_]+", normalized)
    forbidden_hit = _FORBIDDEN_KEYWORDS.intersection(tokens)
    if forbidden_hit:
        raise SQLValidationError(f"Forbidden keyword(s) in query: {sorted(forbidden_hit)}.")

    return _enforce_limit(str(statement).strip())


def _enforce_limit(query: str) -> str:
    match = re.search(r"\bLIMIT\s+(\d+)\b", query, re.IGNORECASE)
    if match:
        requested = int(match.group(1))
        if requested > SQL_AGENT_MAX_ROWS:
            return re.sub(
                r"\bLIMIT\s+\d+\b", f"LIMIT {SQL_AGENT_MAX_ROWS}", query, flags=re.IGNORECASE
            )
        return query
    return f"{query.rstrip(';')} LIMIT {SQL_AGENT_MAX_ROWS}"
