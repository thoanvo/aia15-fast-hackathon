from types import SimpleNamespace

from langchain_app.table_sources import get_source_tables, get_source_tables_for_steps


def test_business_tool_source_tables_are_mapped():
    assert get_source_tables("get_top_products", {}) == ["sales", "products", "regions"]
    assert get_source_tables("get_top_customers", {}) == ["sales", "customers", "regions"]
    assert get_source_tables("get_summary_kpi", {}) == ["sales"]


def test_knowledge_base_and_unknown_tools_have_no_database_sources():
    assert get_source_tables("search_knowledge_base", {}) == []
    assert get_source_tables("unknown_tool", {}) == []
    assert get_source_tables("sql_db_schema", {}) == []


def test_answer_with_sql_source_tables_derived_from_result_query():
    query = "SELECT p.product_name FROM products p JOIN sales s ON s.product_id = p.product_id"

    assert get_source_tables("answer_with_sql", {"question": "..."}, {"query": query}) == ["products", "sales"]


def test_answer_with_sql_with_no_known_table_returns_empty_list():
    assert get_source_tables("answer_with_sql", {"question": "..."}, {"query": "SELECT 1"}) == []
    assert get_source_tables("answer_with_sql", {"question": "..."}, {}) == []


def test_answer_with_sql_with_error_result_returns_empty_list():
    """A failed answer_with_sql call returns {"error": "..."}, not
    {"query": ...} - no tables to attribute."""
    assert get_source_tables("answer_with_sql", {"question": "..."}, {"error": "bad query"}) == []


def test_profit_analysis_source_depends_on_dimension():
    assert get_source_tables("get_profit_analysis", {"dimension": "product"}) == ["sales", "products"]
    assert get_source_tables("get_profit_analysis", {"dimension": "customer"}) == ["sales", "customers"]
    assert get_source_tables("get_profit_analysis", {"dimension": "region"}) == ["sales", "regions"]
    assert get_source_tables("get_profit_analysis", {}) == ["sales", "products"]
    assert get_source_tables("get_profit_analysis", {"dimension": "other"}) == ["sales"]


def test_source_tables_for_steps_deduplicates_in_first_seen_order():
    steps = [
        (SimpleNamespace(tool="get_top_products", tool_input={}), {"rows": []}),
        (SimpleNamespace(tool="get_summary_kpi", tool_input={}), {"revenue": 10}),
        (SimpleNamespace(tool="search_knowledge_base", tool_input={}), "docs"),
    ]

    assert get_source_tables_for_steps(steps) == ["sales", "products", "regions"]


def test_empty_steps_return_no_sources():
    assert get_source_tables_for_steps([]) == []


def test_source_tables_for_steps_dedupes_fixed_tool_and_answer_with_sql_overlap():
    steps = [
        (SimpleNamespace(tool="get_top_products", tool_input={}), {"rows": []}),
        (
            SimpleNamespace(tool="answer_with_sql", tool_input={"question": "..."}),
            {"query": "SELECT * FROM sales JOIN regions r ON r.region_id = sales.region_id"},
        ),
    ]

    assert get_source_tables_for_steps(steps) == ["sales", "products", "regions"]