"""LangChain agent - table sources.

Maps each LangChain tool name (`tools/business_tools.py`,
`tools/retrieval_tool.py`) to the DB table(s) it reads from, so
`chat_service` can attach `source_tables` UI attribution to an answer.
Derived directly from the SQL in `database/dao/*.py` - keep in sync if a
DAO query's joins change. See docs/database_erd.md's "LangChain agent
prompt flow" section.
"""

import re
from typing import Any

# Matches table names following FROM/JOIN, case-insensitive, ignoring
# schema-qualification/quoting - good enough for this project's 4-table
# schema and single-schema (public) database. Not a general SQL parser;
# do not reuse this for anything beyond source-table attribution (SQL
# validation/safety is sql_validation.py's job, not this one's).
_FROM_JOIN_TABLE_RE = re.compile(r"\b(?:FROM|JOIN)\s+([a-zA-Z_][a-zA-Z0-9_]*)", re.IGNORECASE)

_KNOWN_DOMAIN_TABLES = {"products", "customers", "regions", "sales"}


def _tables_from_sql(query: str) -> list[str]:
    """Extract known domain table names referenced in a SQL query's
    FROM/JOIN clauses, for answer_with_sql's source_tables attribution."""
    found = {m.group(1).lower() for m in _FROM_JOIN_TABLE_RE.finditer(query)}
    return sorted(found & _KNOWN_DOMAIN_TABLES)


_TABLE_SOURCES: dict[str, list[str]] = {
    "get_top_products": ["sales", "products", "regions"],
    "get_top_customers": ["sales", "customers", "regions"],
    "get_region_performance": ["sales", "regions"],
    "get_sales_trend": ["sales", "regions"],
    "get_summary_kpi": ["sales"],
    "get_top_products_by_quantity": ["sales", "products", "regions"],
    "get_top_products_by_profit": ["sales", "products", "regions"],
    "get_category_performance": ["sales", "products", "regions"],
    "get_segment_performance": ["sales", "customers", "regions"],
    "get_product_region_performance": ["sales", "products", "regions"],
    "get_customer_purchase_history": ["sales", "customers", "products"],
    "get_low_margin_products": ["sales", "products", "regions"],
    "get_sales_by_date_range": ["sales", "regions"],
    "get_month_over_month_growth": ["sales", "regions"],
    "get_repeat_customer_summary": ["sales", "regions"],
    "search_knowledge_base": [],  # RAG over embedding/ docs, not a DB table
}

# get_profit_analysis's tables depend on its `dimension` argument (see
# database.dao.sales_dao._PROFIT_DIMENSIONS).
_PROFIT_ANALYSIS_TABLES_BY_DIMENSION: dict[str, list[str]] = {
    "product": ["sales", "products"],
    "customer": ["sales", "customers"],
    "region": ["sales", "regions"],
}


def get_source_tables(tool_name: str, tool_args: dict, tool_result: Any = None) -> list[str]:
    """Return the DB table(s) a single tool call reads from.

    `answer_with_sql`'s argument is the user's natural-language question,
    not SQL - it authors/validates/executes the query internally
    (sql_graph.py) - so attribution for that one tool comes from its
    *result* (`{"query": "..."}` on success), not its args.
    """
    if tool_name == "answer_with_sql":
        query = tool_result.get("query", "") if isinstance(tool_result, dict) else ""
        return _tables_from_sql(query)
    if tool_name == "get_profit_analysis":
        dimension = tool_args.get("dimension", "product")
        return _PROFIT_ANALYSIS_TABLES_BY_DIMENSION.get(dimension, ["sales"])
    return _TABLE_SOURCES.get(tool_name, [])


def get_source_tables_for_steps(intermediate_steps: list[tuple[Any, Any]]) -> list[str]:
    """Aggregate unique source tables across an AgentExecutor's `intermediate_steps`.

    `intermediate_steps` is a list of `(AgentAction, observation)` tuples;
    `action.tool` is the tool name, `action.tool_input` the dict of
    arguments it was called with, and `observation` its result.
    """
    tables: list[str] = []
    for action, observation in intermediate_steps:
        for table in get_source_tables(action.tool, action.tool_input or {}, observation):
            if table not in tables:
                tables.append(table)
    return tables
