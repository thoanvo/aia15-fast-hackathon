"""LangChain agent - SQL generation context builder.

Builds the per-question context fed into the SQL-generation prompt: a
structural floor (live schema reflection - always correct, cheap) plus
semantically retrieved business context (table/relationship/metric
knowledge embedded from `embedding/` docs - the same FAISS index
`tools/retrieval_tool.py` uses for background Q&A). Reflection alone
carries no business meaning (a column's type, not what it represents or
how it's meant to be queried); retrieval alone risks pulling an
incomplete/wrong subset for a 4-table schema. Combining both is cheaper
and more reliable than either alone at this schema's size.

Called per-turn (not once at import time) so retrieval reflects the
actual question being asked, not a fixed dump reused for every turn.
"""

from config.settings import SQL_CONTEXT_RETRIEVAL_K
from langchain_app.sql_db import get_sql_database
from langchain_app.vectorstore.store import get_retriever

_SCHEMA_UNAVAILABLE_MESSAGE = "Schema unavailable - call sql_db_schema before writing SQL."


def _structural_floor() -> str:
    """Live-reflected table/column list - always included regardless of
    retrieval quality, so a wrong/incomplete retrieval never leaves SQL
    generation with zero structural grounding. Falls back to a short
    static message if the database isn't reachable (e.g. before a real
    DATABASE_URL is configured)."""
    try:
        return get_sql_database().get_table_info()
    except Exception:  # noqa: BLE001 - DB may be unreachable
        return _SCHEMA_UNAVAILABLE_MESSAGE


def _retrieved_business_context(question: str) -> str:
    """Semantically retrieved business-context chunks (table descriptions,
    relationship semantics, metric formulas) relevant to this question.
    Returns "" on any retrieval failure - SQL generation still has the
    structural floor to work from."""
    try:
        docs = get_retriever(k=SQL_CONTEXT_RETRIEVAL_K).invoke(question)
    except Exception:  # noqa: BLE001 - a retrieval failure must not block SQL generation
        return ""
    if not docs:
        return ""
    return "\n\n".join(doc.page_content for doc in docs)


def build_sql_generation_context(question: str) -> str:
    """Return the full schema context for one question: structural floor
    plus retrieved business context, in that order."""
    parts = [_structural_floor()]
    retrieved = _retrieved_business_context(question)
    if retrieved:
        parts.append("Relevant business context:\n" + retrieved)
    return "\n\n".join(parts)
