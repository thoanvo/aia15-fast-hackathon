"""LangChain tools - business functions.

One tool per Core Business Function (docs/business_description.md > Core
Business Functions), wrapping the matching `database.dao` call. Same 16
functions the additive/backup implementation exposed via a hand-rolled
OpenAI function-calling registry (`backend.function_calling`) - here each
is a `@tool`-decorated function; LangChain turns it into a `StructuredTool`
by inspecting the type hints, and `parse_docstring=True` pulls each
parameter's description from the Google-style `Args:` section (so the
model sees the same per-argument guidance the old JSON-schema registry
gave it).

Every tool body runs through `_safe()`, which catches bad-argument
(`ValueError`) and DB errors and returns `{"error": "..."}` as the tool's
result instead of raising - mirroring the old `function_executor`'s
per-call try/except (a failed call must not crash the whole agent turn).
Note this is *not* the same as LangChain's `handle_tool_error` flag, which
only intercepts `ToolException` - a plain `ValueError`/DB error still
propagates and crashes the turn if left uncaught, which is why every tool
wraps its body in `_safe()` rather than relying on that flag.
"""

from typing import Callable, Literal, Optional

from langchain_core.tools import tool

from database.dao import analytics_dao, customer_dao, product_dao, region_dao, sales_dao


def _limited(limit: int) -> int:
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError("limit must be an integer between 1 and 100")
    return limit


def _safe(call: Callable[[], dict]) -> dict:
    try:
        return call()
    except Exception as exc:  # noqa: BLE001 - handler/DB errors must not crash the agent turn
        return {"error": str(exc)}


@tool(parse_docstring=True)
def get_top_products(limit: int = 5, region: Optional[str] = None) -> dict:
    """Get the top-selling products ranked by total revenue.

    Args:
        limit: How many top products to return.
        region: Optional region name to filter by (e.g. 'Asia', 'Europe'). Omit for all regions.
    """
    def _call():
        products = product_dao.get_top_products(limit=_limited(limit), region=region)
        return {"products": products, "count": len(products), "region": region}
    return _safe(_call)


@tool(parse_docstring=True)
def get_top_customers(limit: int = 5, region: Optional[str] = None) -> dict:
    """Get the top customers ranked by total revenue.

    Args:
        limit: How many top customers to return.
        region: Optional region name to filter by (e.g. 'Asia', 'Europe'). Omit for all regions.
    """
    def _call():
        customers = customer_dao.get_top_customers(limit=_limited(limit), region=region)
        return {"customers": customers, "count": len(customers), "region": region}
    return _safe(_call)


@tool(parse_docstring=True)
def get_region_performance() -> dict:
    """Get revenue and profit performance broken down by region."""
    def _call():
        regions = region_dao.get_region_performance()
        return {"regions": regions, "count": len(regions)}
    return _safe(_call)


@tool(parse_docstring=True)
def get_sales_trend(period: Literal["day", "month", "year"] = "month", region: Optional[str] = None) -> dict:
    """Get the revenue/profit trend over time, bucketed by day, month, or year.

    Args:
        period: Time bucket granularity.
        region: Optional region name to filter by. Omit for all regions.
    """
    def _call():
        trend = sales_dao.get_sales_trend(period=period, region=region)
        return {"trend": trend, "period": period, "region": region}
    return _safe(_call)


@tool(parse_docstring=True)
def get_profit_analysis(dimension: Literal["product", "customer", "region"] = "product") -> dict:
    """Get a profit and margin breakdown by product, customer, or region.

    Args:
        dimension: Dimension to break the profit analysis down by.
    """
    def _call():
        breakdown = sales_dao.get_profit_analysis(dimension=dimension)
        return {"breakdown": breakdown, "dimension": dimension}
    return _safe(_call)


@tool(parse_docstring=True)
def get_summary_kpi(date_from: Optional[str] = None, date_to: Optional[str] = None) -> dict:
    """Get an overall KPI summary: total revenue, total profit, and profit margin.

    Args:
        date_from: Optional ISO date (YYYY-MM-DD) lower bound.
        date_to: Optional ISO date (YYYY-MM-DD) upper bound.
    """
    return _safe(lambda: sales_dao.get_summary_kpi(date_from=date_from, date_to=date_to))


@tool(parse_docstring=True)
def get_top_products_by_quantity(
    limit: int = 5,
    region: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Rank products by units sold.

    Args:
        limit: Number of rows to return (1-100).
        region: Optional region filter.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    def _call():
        products = analytics_dao.get_top_products_by_quantity(_limited(limit), region, date_from, date_to)
        return {"products": products, "region": region}
    return _safe(_call)


@tool(parse_docstring=True)
def get_top_products_by_profit(
    limit: int = 5,
    region: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Rank products by total profit.

    Args:
        limit: Number of rows to return (1-100).
        region: Optional region filter.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    def _call():
        products = analytics_dao.get_top_products_by_profit(_limited(limit), region, date_from, date_to)
        return {"products": products, "region": region}
    return _safe(_call)


@tool(parse_docstring=True)
def get_category_performance(
    region: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None
) -> dict:
    """Compare revenue and profit by product category.

    Args:
        region: Optional region filter.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    return _safe(lambda: {
        "categories": analytics_dao.get_category_performance(region, date_from, date_to),
        "region": region,
    })


@tool(parse_docstring=True)
def get_segment_performance(
    region: Optional[str] = None, date_from: Optional[str] = None, date_to: Optional[str] = None
) -> dict:
    """Compare revenue and profit by customer segment.

    Args:
        region: Optional region filter.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    return _safe(lambda: {
        "segments": analytics_dao.get_segment_performance(region, date_from, date_to),
        "region": region,
    })


@tool(parse_docstring=True)
def get_product_region_performance(
    product_name: Optional[str] = None,
    region: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Compare product performance across regions.

    Args:
        product_name: Optional exact product name to filter by.
        region: Optional region filter.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    return _safe(lambda: {
        "performance": analytics_dao.get_product_region_performance(product_name, region, date_from, date_to),
    })


@tool(parse_docstring=True)
def get_customer_purchase_history(
    customer_name: str, date_from: Optional[str] = None, date_to: Optional[str] = None
) -> dict:
    """List purchases for a customer in an optional date range.

    Args:
        customer_name: Customer name (or partial name) to search for.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    return _safe(lambda: {
        "purchases": analytics_dao.get_customer_purchase_history(customer_name, date_from, date_to),
        "customer_name": customer_name,
    })


@tool(parse_docstring=True)
def get_low_margin_products(
    limit: int = 5,
    region: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> dict:
    """Find products with the lowest observed profit margins.

    Args:
        limit: Number of rows to return (1-100).
        region: Optional region filter.
        date_from: Optional ISO date lower bound.
        date_to: Optional ISO date upper bound.
    """
    def _call():
        products = analytics_dao.get_low_margin_products(_limited(limit), region, date_from, date_to)
        return {"products": products, "region": region}
    return _safe(_call)


@tool(parse_docstring=True)
def get_sales_by_date_range(date_from: str, date_to: str, region: Optional[str] = None) -> dict:
    """Summarize sales between two dates.

    Args:
        date_from: ISO date (YYYY-MM-DD) lower bound.
        date_to: ISO date (YYYY-MM-DD) upper bound.
        region: Optional region filter.
    """
    return _safe(lambda: analytics_dao.get_sales_by_date_range(date_from, date_to, region))


@tool(parse_docstring=True)
def get_month_over_month_growth(region: Optional[str] = None) -> dict:
    """Calculate month-over-month revenue growth.

    Args:
        region: Optional region filter.
    """
    return _safe(lambda: {
        "growth": analytics_dao.get_month_over_month_growth(region),
        "region": region,
    })


@tool(parse_docstring=True)
def get_repeat_customer_summary(region: Optional[str] = None) -> dict:
    """Summarize repeat customers by region.

    Args:
        region: Optional region filter.
    """
    return _safe(lambda: {
        "summary": analytics_dao.get_repeat_customer_summary(region),
        "region": region,
    })


BUSINESS_TOOLS = [
    get_top_products,
    get_top_customers,
    get_region_performance,
    get_sales_trend,
    get_profit_analysis,
    get_summary_kpi,
    get_top_products_by_quantity,
    get_top_products_by_profit,
    get_category_performance,
    get_segment_performance,
    get_product_region_performance,
    get_customer_purchase_history,
    get_low_margin_products,
    get_sales_by_date_range,
    get_month_over_month_growth,
    get_repeat_customer_summary,
]


def get_business_tools() -> list:
    """Return the list of business tools for agent construction (Phase 4)."""
    return BUSINESS_TOOLS
