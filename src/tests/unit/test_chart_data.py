from langchain_app.chart_data import extract_chart_data


def test_extracts_records_from_sales_trend_shaped_result():
    tool_results = [
        {
            "tool": "get_sales_trend",
            "args": {"period": "month"},
            "result": {
                "trend": [
                    {"period": "2025-01", "total_revenue": 1000},
                    {"period": "2025-02", "total_revenue": 1500},
                ],
                "period": "month",
                "region": None,
            },
        }
    ]

    assert extract_chart_data(tool_results) == [
        {"x": "2025-01", "y": 1000},
        {"x": "2025-02", "y": 1500},
    ]


def test_extracts_records_from_run_sql_query_shaped_result():
    tool_results = [
        {
            "tool": "run_sql_query",
            "args": {"query": "SELECT category, SUM(revenue) AS total_revenue FROM sales GROUP BY category"},
            "result": {
                "rows": [
                    {"category": "Electronics", "total_revenue": 5000},
                    {"category": "Accessories", "total_revenue": 2000},
                ],
                "query": "...",
            },
        }
    ]

    assert extract_chart_data(tool_results) == [
        {"x": "Electronics", "y": 5000},
        {"x": "Accessories", "y": 2000},
    ]


def test_returns_none_for_single_kpi_dict_with_no_row_list():
    tool_results = [
        {
            "tool": "get_summary_kpi",
            "args": {},
            "result": {"total_revenue": 10000, "total_profit": 2000, "profit_margin_pct": 20.0},
        }
    ]

    assert extract_chart_data(tool_results) is None


def test_returns_none_when_no_tool_results():
    assert extract_chart_data([]) is None


def test_returns_none_when_result_is_not_a_dict():
    tool_results = [{"tool": "search_knowledge_base", "args": {}, "result": "plain text answer"}]

    assert extract_chart_data(tool_results) is None


def test_returns_none_when_rows_have_no_numeric_column():
    tool_results = [
        {
            "tool": "get_customer_purchase_history",
            "args": {},
            "result": {"purchases": [{"product_name": "Laptop", "sale_date": "2025-01-01"}]},
        }
    ]

    assert extract_chart_data(tool_results) is None


def test_uses_most_recent_tool_result_when_several_calls_happened():
    tool_results = [
        {"tool": "get_summary_kpi", "args": {}, "result": {"total_revenue": 100}},
        {
            "tool": "get_sales_trend",
            "args": {},
            "result": {"trend": [{"period": "2025-01", "total_revenue": 1000}]},
        },
    ]

    assert extract_chart_data(tool_results) == [{"x": "2025-01", "y": 1000}]


def test_skips_leading_id_column_in_favor_of_the_real_metric():
    """get_top_customers's row shape puts customer_id ahead of
    total_revenue - an id is never the metric a chart is about, even
    though it's the first numeric-valued column in the row."""
    tool_results = [
        {
            "tool": "get_top_customers",
            "args": {"limit": 5},
            "result": {
                "customers": [
                    {
                        "customer_id": 101,
                        "customer_name": "Acme Corp",
                        "segment": "Enterprise",
                        "region_name": "Asia",
                        "total_revenue": 50000.0,
                        "total_profit": 12000.0,
                    },
                    {
                        "customer_id": 202,
                        "customer_name": "Globex",
                        "segment": "SMB",
                        "region_name": "Europe",
                        "total_revenue": 30000.0,
                        "total_profit": 8000.0,
                    },
                ],
                "count": 2,
                "region": None,
            },
        }
    ]

    assert extract_chart_data(tool_results) == [
        {"x": "Acme Corp", "y": 50000.0},
        {"x": "Globex", "y": 30000.0},
    ]


def test_skips_leading_id_column_when_picking_the_category_too():
    """get_top_products's row shape puts product_id ahead of
    product_name - "product_id" also matches the "product" category hint
    by substring, which must not win over the real category column
    (product_name) just because it comes first in the row."""
    tool_results = [
        {
            "tool": "get_top_products",
            "args": {"limit": 5},
            "result": {
                "products": [
                    {
                        "product_id": 11,
                        "product_name": "Laptop",
                        "category": "Electronics",
                        "total_revenue": 90000.0,
                        "total_profit": 20000.0,
                        "total_quantity": 120,
                    },
                    {
                        "product_id": 22,
                        "product_name": "Mouse",
                        "category": "Accessories",
                        "total_revenue": 15000.0,
                        "total_profit": 5000.0,
                        "total_quantity": 500,
                    },
                ],
                "count": 2,
                "region": None,
            },
        }
    ]

    assert extract_chart_data(tool_results) == [
        {"x": "Laptop", "y": 90000.0},
        {"x": "Mouse", "y": 15000.0},
    ]


def test_uses_id_column_as_numeric_when_no_other_numeric_column_exists():
    tool_results = [
        {
            "tool": "custom_tool",
            "args": {},
            "result": {"rows": [{"product_name": "Laptop", "product_id": 1}]},
        }
    ]

    assert extract_chart_data(tool_results) == [{"x": "Laptop", "y": 1}]


def test_falls_back_to_key_name_hint_when_no_string_column_present():
    tool_results = [
        {
            "tool": "custom_tool",
            "args": {},
            "result": {"rows": [{"year": 2024, "total": 100}, {"year": 2025, "total": 200}]},
        }
    ]

    assert extract_chart_data(tool_results) == [{"x": 2024, "y": 100}, {"x": 2025, "y": 200}]
