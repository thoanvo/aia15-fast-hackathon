"""DAO Layer - Products.

Data access for the Products table
(docs/business_description.md > Database Schema: Products table).
Backs langchain_app.tools.business_tools.
"""

from sqlalchemy import text

from database.connection.connection_pool import get_session, serialize_row

_TOP_PRODUCTS_SQL = """
    SELECT
        p.product_id,
        p.product_name,
        p.category,
        SUM(s.revenue)  AS total_revenue,
        SUM(s.profit)   AS total_profit,
        SUM(s.quantity) AS total_quantity
    FROM sales s
    JOIN products p ON p.product_id = s.product_id
    JOIN regions r  ON r.region_id = s.region_id
    WHERE (:region IS NULL OR r.region_name = :region)
    GROUP BY p.product_id, p.product_name, p.category
    ORDER BY total_revenue DESC
    LIMIT :limit
"""


def get_top_products(limit: int = 5, region: str | None = None) -> list[dict]:
    """Top products by total revenue, optionally filtered by region name."""
    with get_session() as session:
        rows = session.execute(
            text(_TOP_PRODUCTS_SQL), {"limit": limit, "region": region}
        ).mappings().all()
        return [serialize_row(row) for row in rows]
