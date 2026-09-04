"""DAO Layer - Customers.

Data access for the Customers table
(docs/business_description.md > Database Schema: Customers table).
Backs langchain_app.tools.business_tools.
"""

from sqlalchemy import text

from database.connection.connection_pool import get_session, serialize_row

_TOP_CUSTOMERS_SQL = """
    SELECT
        c.customer_id,
        c.customer_name,
        c.segment,
        r.region_name,
        SUM(s.revenue) AS total_revenue,
        SUM(s.profit)  AS total_profit
    FROM sales s
    JOIN customers c ON c.customer_id = s.customer_id
    JOIN regions r   ON r.region_id = s.region_id
    WHERE (:region IS NULL OR r.region_name = :region)
    GROUP BY c.customer_id, c.customer_name, c.segment, r.region_name
    ORDER BY total_revenue DESC
    LIMIT :limit
"""


def get_top_customers(limit: int = 5, region: str | None = None) -> list[dict]:
    """Top customers by total revenue, optionally filtered by region name."""
    with get_session() as session:
        rows = session.execute(
            text(_TOP_CUSTOMERS_SQL), {"limit": limit, "region": region}
        ).mappings().all()
        return [serialize_row(row) for row in rows]
