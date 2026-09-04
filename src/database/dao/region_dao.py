"""DAO Layer - Regions.

Data access for the Regions table
(docs/business_description.md > Database Schema: Regions table).
Backs langchain_app.tools.business_tools (get_region_performance).
"""

from sqlalchemy import text

from database.connection.connection_pool import get_session, serialize_row

_REGION_PERFORMANCE_SQL = """
    SELECT
        r.region_id,
        r.region_name,
        r.country,
        SUM(s.revenue)                         AS total_revenue,
        SUM(s.profit)                          AS total_profit,
        COUNT(DISTINCT s.customer_id)          AS customer_count,
        COUNT(*)                               AS order_count
    FROM sales s
    JOIN regions r ON r.region_id = s.region_id
    GROUP BY r.region_id, r.region_name, r.country
    ORDER BY total_revenue DESC
"""


def get_region_performance() -> list[dict]:
    """Revenue/profit performance aggregated per region."""
    with get_session() as session:
        rows = session.execute(text(_REGION_PERFORMANCE_SQL)).mappings().all()
        return [serialize_row(row) for row in rows]
