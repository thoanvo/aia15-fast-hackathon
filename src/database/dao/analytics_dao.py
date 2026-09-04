"""Additional read-only analytics queries for the business functions."""

from sqlalchemy import text

from database.connection.connection_pool import get_session, serialize_row


def _rows(sql: str, parameters: dict) -> list[dict]:
    with get_session() as session:
        result = session.execute(text(sql), parameters).mappings().all()
        return [serialize_row(row) for row in result]


_DATE_FILTER = """
    AND (:date_from IS NULL OR s.sale_date >= :date_from)
    AND (:date_to IS NULL OR s.sale_date <= :date_to)
"""


def get_top_products_by_quantity(limit=5, region=None, date_from=None, date_to=None):
    return _rows(f"""
        SELECT p.product_id, p.product_name, p.category,
               SUM(s.quantity) AS total_quantity, SUM(s.revenue) AS total_revenue
        FROM sales s JOIN products p ON p.product_id = s.product_id
        JOIN regions r ON r.region_id = s.region_id
        WHERE (:region IS NULL OR r.region_name = :region) {_DATE_FILTER}
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY total_quantity DESC LIMIT :limit
    """, {"limit": limit, "region": region, "date_from": date_from, "date_to": date_to})


def get_top_products_by_profit(limit=5, region=None, date_from=None, date_to=None):
    return _rows(f"""
        SELECT p.product_id, p.product_name, p.category,
               SUM(s.profit) AS total_profit, SUM(s.revenue) AS total_revenue,
               ROUND(SUM(s.profit) / NULLIF(SUM(s.revenue), 0) * 100, 2) AS profit_margin_pct
        FROM sales s JOIN products p ON p.product_id = s.product_id
        JOIN regions r ON r.region_id = s.region_id
        WHERE (:region IS NULL OR r.region_name = :region) {_DATE_FILTER}
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY total_profit DESC LIMIT :limit
    """, {"limit": limit, "region": region, "date_from": date_from, "date_to": date_to})


def get_category_performance(region=None, date_from=None, date_to=None):
    return _rows(f"""
        SELECT p.category, SUM(s.revenue) AS total_revenue,
               SUM(s.profit) AS total_profit, SUM(s.quantity) AS total_quantity,
               COUNT(*) AS order_count
        FROM sales s JOIN products p ON p.product_id = s.product_id
        JOIN regions r ON r.region_id = s.region_id
        WHERE (:region IS NULL OR r.region_name = :region) {_DATE_FILTER}
        GROUP BY p.category ORDER BY total_revenue DESC
    """, {"region": region, "date_from": date_from, "date_to": date_to})


def get_segment_performance(region=None, date_from=None, date_to=None):
    return _rows(f"""
        SELECT c.segment, SUM(s.revenue) AS total_revenue,
               SUM(s.profit) AS total_profit, COUNT(DISTINCT c.customer_id) AS customer_count,
               COUNT(*) AS order_count
        FROM sales s JOIN customers c ON c.customer_id = s.customer_id
        JOIN regions r ON r.region_id = s.region_id
        WHERE (:region IS NULL OR r.region_name = :region) {_DATE_FILTER}
        GROUP BY c.segment ORDER BY total_revenue DESC
    """, {"region": region, "date_from": date_from, "date_to": date_to})


def get_product_region_performance(product_name=None, region=None, date_from=None, date_to=None):
    return _rows(f"""
        SELECT p.product_name, r.region_name, SUM(s.revenue) AS total_revenue,
               SUM(s.profit) AS total_profit, SUM(s.quantity) AS total_quantity
        FROM sales s JOIN products p ON p.product_id = s.product_id
        JOIN regions r ON r.region_id = s.region_id
        WHERE (:product_name IS NULL OR p.product_name = :product_name)
          AND (:region IS NULL OR r.region_name = :region) {_DATE_FILTER}
        GROUP BY p.product_name, r.region_name ORDER BY total_revenue DESC
    """, {"product_name": product_name, "region": region, "date_from": date_from, "date_to": date_to})


def get_customer_purchase_history(customer_name, date_from=None, date_to=None):
    return _rows(f"""
        SELECT c.customer_name, s.sale_date, p.product_name, s.quantity,
               s.revenue, s.profit
        FROM sales s JOIN customers c ON c.customer_id = s.customer_id
        JOIN products p ON p.product_id = s.product_id
        WHERE c.customer_name ILIKE :customer_name {_DATE_FILTER}
        ORDER BY s.sale_date DESC
    """, {"customer_name": f"%{customer_name}%", "date_from": date_from, "date_to": date_to})


def get_low_margin_products(limit=5, region=None, date_from=None, date_to=None):
    return _rows(f"""
        SELECT p.product_id, p.product_name, p.category, SUM(s.revenue) AS total_revenue,
               SUM(s.profit) AS total_profit,
               ROUND(SUM(s.profit) / NULLIF(SUM(s.revenue), 0) * 100, 2) AS profit_margin_pct
        FROM sales s JOIN products p ON p.product_id = s.product_id
        JOIN regions r ON r.region_id = s.region_id
        WHERE (:region IS NULL OR r.region_name = :region) {_DATE_FILTER}
        GROUP BY p.product_id, p.product_name, p.category
        ORDER BY profit_margin_pct ASC LIMIT :limit
    """, {"limit": limit, "region": region, "date_from": date_from, "date_to": date_to})


def get_sales_by_date_range(date_from, date_to, region=None):
    rows = _rows("""
        SELECT COUNT(*) AS order_count, SUM(s.quantity) AS total_quantity,
               SUM(s.revenue) AS total_revenue, SUM(s.profit) AS total_profit,
               ROUND(SUM(s.profit) / NULLIF(SUM(s.revenue), 0) * 100, 2) AS profit_margin_pct
        FROM sales s JOIN regions r ON r.region_id = s.region_id
        WHERE s.sale_date BETWEEN :date_from AND :date_to
          AND (:region IS NULL OR r.region_name = :region)
    """, {"date_from": date_from, "date_to": date_to, "region": region})
    return rows[0] if rows else {}


def get_month_over_month_growth(region=None):
    return _rows("""
        WITH monthly AS (
            SELECT date_trunc('month', s.sale_date) AS month,
                   SUM(s.revenue) AS total_revenue, SUM(s.profit) AS total_profit
            FROM sales s JOIN regions r ON r.region_id = s.region_id
            WHERE (:region IS NULL OR r.region_name = :region)
            GROUP BY month
        )
        SELECT month, total_revenue, total_profit,
               LAG(total_revenue) OVER (ORDER BY month) AS previous_revenue,
               ROUND((total_revenue - LAG(total_revenue) OVER (ORDER BY month))
                     / NULLIF(LAG(total_revenue) OVER (ORDER BY month), 0) * 100, 2)
                     AS revenue_growth_pct
        FROM monthly ORDER BY month
    """, {"region": region})


def get_repeat_customer_summary(region=None):
    return _rows("""
        SELECT r.region_name, COUNT(*) AS customer_count,
               COUNT(*) FILTER (WHERE order_count > 1) AS repeat_customer_count
        FROM (
            SELECT s.customer_id, s.region_id, COUNT(*) AS order_count
            FROM sales s GROUP BY s.customer_id, s.region_id
        ) grouped JOIN regions r ON r.region_id = grouped.region_id
        WHERE (:region IS NULL OR r.region_name = :region)
        GROUP BY r.region_name ORDER BY r.region_name
    """, {"region": region})
