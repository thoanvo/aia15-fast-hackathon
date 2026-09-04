import pytest

from langchain_app.tools import business_tools


def test_limited_accepts_range_and_rejects_invalid_values():
    assert business_tools._limited(1) == 1
    assert business_tools._limited(100) == 100

    for value in (0, -1, 101, "5", 5.0):
        with pytest.raises(ValueError):
            business_tools._limited(value)


def test_get_top_products_wraps_dao_result(monkeypatch):
    calls = []

    def fake_get_top_products(limit, region):
        calls.append((limit, region))
        return [{"product_name": "Laptop", "total_revenue": 1000}]

    monkeypatch.setattr(business_tools.product_dao, "get_top_products", fake_get_top_products)

    result = business_tools.get_top_products.invoke({"limit": 3, "region": "Asia"})

    assert calls == [(3, "Asia")]
    assert result == {
        "products": [{"product_name": "Laptop", "total_revenue": 1000}],
        "count": 1,
        "region": "Asia",
    }


def test_get_top_products_returns_error_when_dao_fails(monkeypatch):
    def fail_get_top_products(limit, region):
        raise RuntimeError("database unavailable")

    monkeypatch.setattr(business_tools.product_dao, "get_top_products", fail_get_top_products)

    assert business_tools.get_top_products.invoke({}) == {"error": "database unavailable"}


def test_analytics_tool_forwards_filters(monkeypatch):
    calls = []

    def fake_get_top_products_by_profit(limit, region, date_from, date_to):
        calls.append((limit, region, date_from, date_to))
        return [{"product_name": "Laptop"}]

    monkeypatch.setattr(
        business_tools.analytics_dao,
        "get_top_products_by_profit",
        fake_get_top_products_by_profit,
    )

    result = business_tools.get_top_products_by_profit.invoke(
        {"limit": 2, "region": "Europe", "date_from": "2025-01-01", "date_to": "2025-03-31"}
    )

    assert calls == [(2, "Europe", "2025-01-01", "2025-03-31")]
    assert result == {"products": [{"product_name": "Laptop"}], "region": "Europe"}


def test_get_business_tools_contains_unique_tool_names():
    tools = business_tools.get_business_tools()
    names = [tool.name for tool in tools]

    assert len(names) == 16
    assert len(names) == len(set(names))
    assert "get_top_products" in names
    assert "get_repeat_customer_summary" in names