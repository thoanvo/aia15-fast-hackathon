"""LangChain agent - chart-data extraction.

Deterministic heuristic (no LLM call) that inspects a turn's tool results
and decides whether the shape is chart-worthy: a list of row dicts with
one category/date-like column and one numeric column. Not every tool
result qualifies - a single KPI dict (get_summary_kpi) has no row list to
chart at all, and that's the common case, not an error; this returns
None rather than raising or forcing a chart.
"""

from typing import Any, Optional

# Key-name hints used only as a fallback when no string-valued column is
# present in the row shape (e.g. a period bucket stored as a date/int).
_CATEGORY_KEY_HINTS = ("date", "period", "month", "day", "year", "region", "category", "segment", "name", "product")


def _find_row_list(result: Any) -> Optional[list[dict]]:
    """Find the first list-of-dicts value inside a tool result dict -
    e.g. get_sales_trend's "trend", get_top_products's "products",
    run_sql_query's "rows"."""
    if not isinstance(result, dict):
        return None
    for value in result.values():
        if isinstance(value, list) and value and all(isinstance(row, dict) for row in value):
            return value
    return None


def _looks_like_id_column(key: str) -> bool:
    """True for a primary/foreign-key-shaped column name (e.g. customer_id,
    product_id, id) - these are row identifiers, not a chart-worthy metric,
    even though their value is numeric."""
    lowered = key.lower()
    return lowered == "id" or lowered.endswith("_id")


def _pick_columns(rows: list[dict]) -> Optional[tuple[str, str]]:
    """Pick one category-like column and one numeric column from the row
    shape (the first row is representative - every fixed tool/SQL result
    row has a uniform shape).

    Category detection is tried by key-name hint *first*, ahead of
    "first string-valued column" - a column like "year": 2024 is a
    category/time-bucket even though its value is numeric, and must not
    be picked as the numeric (y) column instead.

    Both category and numeric detection skip id-shaped columns
    (customer_id, product_id, ...) first, falling back to them only if
    nothing else qualifies:
    - Numeric: e.g. get_top_customers's row shape has customer_id ahead of
      total_revenue, and an id is never the metric a chart-worthy answer
      is about.
    - Category: an id-shaped key can still match a category hint by
      substring - "product_id" contains "product", "region_id" contains
      "region" - which would otherwise win over the real category column
      (product_name, region_name) since it comes first in the row.
    """
    sample = rows[0]
    non_id_keys = [key for key in sample if not _looks_like_id_column(key)]
    id_keys = [key for key in sample if _looks_like_id_column(key)]

    category_col = None
    for key in non_id_keys:
        if any(hint in key.lower() for hint in _CATEGORY_KEY_HINTS):
            category_col = key
            break
    if category_col is None:
        for key in non_id_keys:
            if isinstance(sample[key], str):
                category_col = key
                break
    if category_col is None:
        for key in id_keys:
            if any(hint in key.lower() for hint in _CATEGORY_KEY_HINTS):
                category_col = key
                break
    if category_col is None:
        for key in id_keys:
            if isinstance(sample[key], str):
                category_col = key
                break

    numeric_col = None
    fallback_id_numeric_col = None
    for key, value in sample.items():
        if key == category_col:
            continue
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            if _looks_like_id_column(key):
                if fallback_id_numeric_col is None:
                    fallback_id_numeric_col = key
                continue
            numeric_col = key
            break
    if numeric_col is None:
        numeric_col = fallback_id_numeric_col

    if category_col is None or numeric_col is None:
        return None
    return category_col, numeric_col


def extract_chart_data(tool_results: list[dict]) -> Optional[list[dict]]:
    """Return chart-ready [{"x": ..., "y": ...}, ...] records derived from
    the turn's most recent tool result, or None if nothing chart-worthy
    was found (no rows, or no category/numeric column pair)."""
    if not tool_results:
        return None
    result = tool_results[-1].get("result")
    rows = _find_row_list(result)
    if not rows:
        return None
    columns = _pick_columns(rows)
    if columns is None:
        return None
    category_col, numeric_col = columns
    records = [{"x": row.get(category_col), "y": row[numeric_col]} for row in rows if numeric_col in row]
    return records or None
