"""DAO Layer - Sales.

Data access for the Sales table
(docs/business_description.md > Database Schema: Sales table).
Backs langchain_app.tools.business_tools (sales trend, profit, KPI tools).
"""

from sqlalchemy import text

from database.connection.connection_pool import get_session, serialize_row

_VALID_TREND_PERIODS = {"day", "month", "year"}

_SALES_TREND_SQL_TEMPLATE = """
    SELECT
        date_trunc('{period}', s.sale_date) AS period,
        SUM(s.revenue)  AS total_revenue,
        SUM(s.profit)   AS total_profit,
        SUM(s.quantity) AS total_quantity
    FROM sales s
    JOIN regions r ON r.region_id = s.region_id
    WHERE (:region IS NULL OR r.region_name = :region)
    GROUP BY period
    ORDER BY period
"""

# dimension -> (id column, name column, join clause)
_PROFIT_DIMENSIONS = {
    "product": ("p.product_id", "p.product_name", "JOIN products p ON p.product_id = s.product_id"),
    "customer": ("c.customer_id", "c.customer_name", "JOIN customers c ON c.customer_id = s.customer_id"),
    "region": ("r.region_id", "r.region_name", "JOIN regions r ON r.region_id = s.region_id"),
}

_SUMMARY_KPI_SQL = """
    SELECT
        SUM(revenue)                                            AS total_revenue,
        SUM(profit)                                             AS total_profit,
        ROUND(SUM(profit) / NULLIF(SUM(revenue), 0) * 100, 2)   AS profit_margin_pct,
        COUNT(*)                                                AS total_orders
    FROM sales
    WHERE (:date_from IS NULL OR sale_date >= :date_from)
      AND (:date_to IS NULL OR sale_date <= :date_to)
"""


def get_sales_trend(period: str = "month", region: str | None = None) -> list[dict]:
    """Revenue/profit trend over time, bucketed by day/month/year."""
    if period not in _VALID_TREND_PERIODS:
        raise ValueError(f"Unsupported period '{period}'. Expected one of {_VALID_TREND_PERIODS}.")

    sql = _SALES_TREND_SQL_TEMPLATE.format(period=period)
    with get_session() as session:
        rows = session.execute(text(sql), {"region": region}).mappings().all()
        return [serialize_row(row) for row in rows]


def get_profit_analysis(dimension: str = "product") -> list[dict]:
    """Profit breakdown grouped by 'product', 'customer', or 'region'."""
    if dimension not in _PROFIT_DIMENSIONS:
        raise ValueError(f"Unsupported dimension '{dimension}'. Expected one of {set(_PROFIT_DIMENSIONS)}.")

    id_col, name_col, join_clause = _PROFIT_DIMENSIONS[dimension]
    sql = f"""
        SELECT
            {id_col} AS id,
            {name_col} AS name,
            SUM(s.revenue)                                          AS total_revenue,
            SUM(s.profit)                                           AS total_profit,
            ROUND(SUM(s.profit) / NULLIF(SUM(s.revenue), 0) * 100, 2) AS profit_margin_pct
        FROM sales s
        {join_clause}
        GROUP BY {id_col}, {name_col}
        ORDER BY total_profit DESC
    """
    with get_session() as session:
        rows = session.execute(text(sql)).mappings().all()
        return [serialize_row(row) for row in rows]


def get_summary_kpi(date_from: str | None = None, date_to: str | None = None) -> dict:
    """Overall revenue/profit/margin KPI summary, optionally scoped to a date range."""
    with get_session() as session:
        row = session.execute(
            text(_SUMMARY_KPI_SQL), {"date_from": date_from, "date_to": date_to}
        ).mappings().first()
        return serialize_row(row) if row else {}
