"""LangChain tools - dynamic SQL over the reflected schema.

Two tools, additive to business_tools.py's fixed 16: `sql_db_schema`
(on-demand schema lookup) and `answer_with_sql` (the full generate-
validate-execute-retry pipeline, run as a LangGraph sub-graph -
sql_graph.py). Both follow business_tools.py's `_safe()` convention - a
bad call returns {"error": ...} instead of raising and crashing the
agent turn.

`answer_with_sql` takes the user's natural-language question, not a
hand-written SQL string - SQL authorship happens inside the graph's own
generate_sql node (its own dedicated LLM call, grounded in schema
context), not in the outer tool-calling model's argument-filling. The
graph bounds and retries its own generate/validate/execute loop
internally (see sql_graph.py), so this tool always resolves - success or
a clean final failure - within a single outer tool call; no outer-level
attempt counter is needed here.
"""

from langchain_core.tools import tool

from langchain_app.sql_db import get_sql_database
from langchain_app.sql_graph import run_sql_graph


def _safe(call):
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - mirrors business_tools.py's _safe()
        return {"error": str(exc)}


@tool(parse_docstring=True)
def sql_db_schema(table_names: str) -> str:
    """Get column definitions for one or more tables, comma-separated.

    Use this to double-check exact column names/types before asking a
    question that no other business tool answers. Valid tables: products,
    customers, regions, sales.

    Args:
        table_names: Comma-separated table names, e.g. "sales,products".
    """
    def _call():
        names = [t.strip() for t in table_names.split(",") if t.strip()]
        return get_sql_database().get_table_info(table_names=names)
    return _safe(_call)


@tool(parse_docstring=True)
def answer_with_sql(question: str) -> dict:
    """Answer a data question that no fixed business tool covers, by
    generating, validating, and running a read-only SQL query for it.

    Pass the user's own question in natural language - do not write SQL
    yourself. Only use this when no fixed business tool's description
    matches the question's shape.

    Args:
        question: The user's original data question, in natural language.
    """
    def _call():
        final_state = run_sql_graph(question)
        if final_state.get("error"):
            return {"error": final_state["error"]}
        return {"rows": final_state.get("rows") or [], "query": final_state.get("generated_sql", "")}
    return _safe(_call)


def get_sql_tools() -> list:
    """Return the dynamic-SQL tool pair for agent construction."""
    return [sql_db_schema, answer_with_sql]
