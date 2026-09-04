"""DEV-ONLY: run the backend with the database layer faked out.

Use this when you can't reach the real Neon PostgreSQL database (e.g. no
network/firewall permission) but still want to smoke-test that the app
works end to end: controller -> service -> LangChain agent -> business
tools -> "DAO" -> in-memory fake data -> back to the model -> answer.

This does NOT modify production code. It monkeypatches the `database.dao.*`
functions that `langchain_app.tools.business_tools` calls (the same
technique used to verify database-dependent phases without a live DB
during development - see docs/10_implementation_guide.md) before starting
the real FastAPI app. `database.connection.connection_pool` is patched
only for its `check_connection()` health check.

The dynamic-SQL agent path (`answer_with_sql`/`sql_db_schema`,
`langchain_app.sql_db`) bypasses `database.dao.*` entirely - it talks
directly to a real SQLAlchemy engine, since the LLM generates arbitrary
SQL rather than calling a fixed Python function. Faking that path means
swapping in a real, queryable database, not monkeypatching functions -
see `dev_fake_sql_engine.py` for the in-memory SQLite stand-in this
script wires into `langchain_app.sql_db.engine`/`readonly_engine`. Those
tools are always registered on the agent (regardless of
`FIXED_TOOLS_ENABLED`), so this fake engine is needed for every run of
this script.

Still requires a real `OPENAI_API_KEY` (and `OPENAI_BASE_URL`, if going
through a gateway) in `.env` - only the database is faked, not the LLM.
`DATABASE_URL` in `.env` can be any placeholder string; it's never
actually connected to (SQLAlchemy's `create_engine()` is lazy, and this
script also fakes the health check) - real Postgres and the fake SQLite
engine used for the SQL-agent path are entirely independent of each
other.

Import order matters here on Windows: `langchain_app.tools.business_tools`
is imported first, on purpose, before `database.dao.*` is imported again
for patching - see `langchain_app/tools/__init__.py`'s docstring for why
(SQLAlchemy's compiled Cython extensions loading before torch breaks
torch's DLL init; importing the tools package first forces the embedding
model to load first instead).

No hot-reload here (uvicorn's --reload re-imports the app fresh per
worker, which would lose these patches) - restart the script after code
changes.

Usage (from src/):
    python dev_fake_backend.py
"""

import uvicorn

import langchain_app.tools.business_tools  # noqa: F401  (import order - see module docstring)

import database.connection.connection_pool as connection_pool
import database.dao.analytics_dao as analytics_dao
import database.dao.customer_dao as customer_dao
import database.dao.product_dao as product_dao
import database.dao.region_dao as region_dao
import database.dao.sales_dao as sales_dao
import langchain_app.sql_db as sql_db
from dev_fake_sql_engine import build_fake_sql_engine

# Fake data reflects the current mock catalog/regions in
# database/mock_data/sample_data.sql (10 regions, 15 products,
# randomly-generated "Customer_N" customers) - not tied to a specific
# scripted docs example, since that dataset is now randomized per run
# and can't be reproduced exactly here. "East Asia" stands in for the
# old dataset's single "Asia" region in the region-filtered examples
# below.

_ALL_PRODUCTS = [
    {"product_id": 2, "product_name": "Server", "category": "Infrastructure", "total_revenue": 3780000.0, "total_profit": 1530000.0, "total_quantity": 900},
    {"product_id": 1, "product_name": "Smartphone", "category": "Electronics", "total_revenue": 3634800.0, "total_profit": 1814800.0, "total_quantity": 5200},
    {"product_id": 3, "product_name": "Storage NAS", "category": "Infrastructure", "total_revenue": 1595000.0, "total_profit": 715000.0, "total_quantity": 1100},
    {"product_id": 12, "product_name": "Firewall Appliance", "category": "Networking", "total_revenue": 1440000.0, "total_profit": 840000.0, "total_quantity": 1200},
    {"product_id": 6, "product_name": "Projector", "category": "Electronics", "total_revenue": 855000.0, "total_profit": 405000.0, "total_quantity": 900},
]

_EAST_ASIA_PRODUCTS = [
    {"product_id": 1, "product_name": "Smartphone", "category": "Electronics", "total_revenue": 1398000.0, "total_profit": 698000.0, "total_quantity": 2000},
    {"product_id": 2, "product_name": "Server", "category": "Infrastructure", "total_revenue": 840000.0, "total_profit": 340000.0, "total_quantity": 200},
    {"product_id": 3, "product_name": "Storage NAS", "category": "Infrastructure", "total_revenue": 435000.0, "total_profit": 195000.0, "total_quantity": 300},
]

_ALL_CUSTOMERS = [
    {"customer_id": 42, "customer_name": "Customer_042", "segment": "Enterprise", "region_name": "East Asia", "total_revenue": 612000.0, "total_profit": 254000.0},
    {"customer_id": 178, "customer_name": "Customer_178", "segment": "Enterprise", "region_name": "South Asia", "total_revenue": 587500.0, "total_profit": 238000.0},
    {"customer_id": 5, "customer_name": "Customer_005", "segment": "Enterprise", "region_name": "Oceania", "total_revenue": 540000.0, "total_profit": 210000.0},
    {"customer_id": 231, "customer_name": "Customer_231", "segment": "SMB", "region_name": "East Asia", "total_revenue": 398000.0, "total_profit": 145000.0},
    {"customer_id": 99, "customer_name": "Customer_099", "segment": "Enterprise", "region_name": "Western Europe", "total_revenue": 372000.0, "total_profit": 138000.0},
]

_EAST_ASIA_CUSTOMERS = [c for c in _ALL_CUSTOMERS if c["region_name"] == "East Asia"]

_REGIONS = [
    {"region_id": 4, "region_name": "East Asia", "country": "Japan", "total_revenue": 3850000.0, "total_profit": 1540000.0, "customer_count": 34, "order_count": 210},
    {"region_id": 5, "region_name": "South Asia", "country": "India", "total_revenue": 3220000.0, "total_profit": 1260000.0, "customer_count": 31, "order_count": 188},
    {"region_id": 6, "region_name": "Western Europe", "country": "France", "total_revenue": 2640000.0, "total_profit": 1010000.0, "customer_count": 29, "order_count": 165},
    {"region_id": 1, "region_name": "Oceania", "country": "Australia", "total_revenue": 2180000.0, "total_profit": 860000.0, "customer_count": 27, "order_count": 150},
    {"region_id": 7, "region_name": "Northern Europe", "country": "UK", "total_revenue": 1890000.0, "total_profit": 740000.0, "customer_count": 26, "order_count": 140},
    {"region_id": 10, "region_name": "Central Asia", "country": "Kazakhstan", "total_revenue": 1540000.0, "total_profit": 610000.0, "customer_count": 25, "order_count": 118},
    {"region_id": 2, "region_name": "Middle East", "country": "UAE", "total_revenue": 1320000.0, "total_profit": 520000.0, "customer_count": 24, "order_count": 105},
    {"region_id": 3, "region_name": "Africa", "country": "South Africa", "total_revenue": 1050000.0, "total_profit": 405000.0, "customer_count": 23, "order_count": 92},
    {"region_id": 9, "region_name": "Eastern Europe", "country": "Poland", "total_revenue": 870000.0, "total_profit": 330000.0, "customer_count": 22, "order_count": 78},
    {"region_id": 8, "region_name": "Central America", "country": "Mexico", "total_revenue": 620000.0, "total_profit": 235000.0, "customer_count": 21, "order_count": 62},
]

_TREND = [
    {"period": f"2026-{month:02d}-01", "total_revenue": revenue, "total_profit": round(revenue * 0.36, 2), "total_quantity": quantity}
    for month, revenue, quantity in [
        (1, 620000.0, 780), (2, 655000.0, 824), (3, 690000.0, 861),
        (4, 725000.0, 898), (5, 760000.0, 934), (6, 800000.0, 972),
    ]
]

_PROFIT_BY_DIMENSION = {
    "product": [
        {"id": p["product_id"], "name": p["product_name"], "total_revenue": p["total_revenue"],
         "total_profit": p["total_profit"], "profit_margin_pct": round(p["total_profit"] / p["total_revenue"] * 100, 2)}
        for p in _ALL_PRODUCTS
    ],
    "customer": [
        {"id": c["customer_id"], "name": c["customer_name"], "total_revenue": c["total_revenue"],
         "total_profit": c["total_profit"], "profit_margin_pct": round(c["total_profit"] / c["total_revenue"] * 100, 2)}
        for c in _ALL_CUSTOMERS
    ],
    "region": [
        {"id": r["region_id"], "name": r["region_name"], "total_revenue": r["total_revenue"],
         "total_profit": r["total_profit"], "profit_margin_pct": round(r["total_profit"] / r["total_revenue"] * 100, 2)}
        for r in _REGIONS
    ],
}

_SUMMARY_KPI = {"total_revenue": 19180000.0, "total_profit": 7510000.0, "profit_margin_pct": 39.16, "total_orders": 1308}

_ANALYTICS_PRODUCTS_BY_QUANTITY = [
    {"product_id": 1, "product_name": "Smartphone", "category": "Electronics", "total_quantity": 5200, "total_revenue": 3634800.0},
    {"product_id": 12, "product_name": "Firewall Appliance", "category": "Networking", "total_quantity": 1200, "total_revenue": 1440000.0},
    {"product_id": 3, "product_name": "Storage NAS", "category": "Infrastructure", "total_quantity": 1100, "total_revenue": 1595000.0},
    {"product_id": 2, "product_name": "Server", "category": "Infrastructure", "total_quantity": 900, "total_revenue": 3780000.0},
    {"product_id": 6, "product_name": "Projector", "category": "Electronics", "total_quantity": 900, "total_revenue": 855000.0},
]

_ANALYTICS_PRODUCTS_BY_PROFIT = [
    {"product_id": 1, "product_name": "Smartphone", "category": "Electronics", "total_profit": 1814800.0, "total_revenue": 3634800.0, "profit_margin_pct": 49.93},
    {"product_id": 2, "product_name": "Server", "category": "Infrastructure", "total_profit": 1530000.0, "total_revenue": 3780000.0, "profit_margin_pct": 40.48},
    {"product_id": 12, "product_name": "Firewall Appliance", "category": "Networking", "total_profit": 840000.0, "total_revenue": 1440000.0, "profit_margin_pct": 58.33},
    {"product_id": 3, "product_name": "Storage NAS", "category": "Infrastructure", "total_profit": 715000.0, "total_revenue": 1595000.0, "profit_margin_pct": 44.83},
    {"product_id": 6, "product_name": "Projector", "category": "Electronics", "total_profit": 405000.0, "total_revenue": 855000.0, "profit_margin_pct": 47.37},
]

_CATEGORY_PERFORMANCE = [
    {"category": "Infrastructure", "total_revenue": 6500000.0, "total_profit": 2700000.0, "total_quantity": 2600, "order_count": 410},
    {"category": "Electronics", "total_revenue": 5900000.0, "total_profit": 2450000.0, "total_quantity": 9200, "order_count": 520},
    {"category": "Networking", "total_revenue": 3400000.0, "total_profit": 1750000.0, "total_quantity": 8100, "order_count": 380},
    {"category": "Software", "total_revenue": 1980000.0, "total_profit": 1340000.0, "total_quantity": 15800, "order_count": 640},
    {"category": "Accessories", "total_revenue": 1400000.0, "total_profit": 830000.0, "total_quantity": 21000, "order_count": 710},
]

_SEGMENT_PERFORMANCE = [
    {"segment": "Enterprise", "total_revenue": 11200000.0, "total_profit": 4600000.0, "customer_count": 120, "order_count": 780},
    {"segment": "SMB", "total_revenue": 6300000.0, "total_profit": 2400000.0, "customer_count": 120, "order_count": 460},
    {"segment": "Individual", "total_revenue": 1680000.0, "total_profit": 510000.0, "customer_count": 60, "order_count": 210},
]

_PRODUCT_REGION_PERFORMANCE = [
    {"product_name": "Smartphone", "region_name": "East Asia", "total_revenue": 1398000.0, "total_profit": 698000.0, "total_quantity": 2000},
    {"product_name": "Smartphone", "region_name": "South Asia", "total_revenue": 980000.0, "total_profit": 490000.0, "total_quantity": 1400},
    {"product_name": "Smartphone", "region_name": "Western Europe", "total_revenue": 629100.0, "total_profit": 314100.0, "total_quantity": 900},
    {"product_name": "Server", "region_name": "East Asia", "total_revenue": 840000.0, "total_profit": 340000.0, "total_quantity": 200},
    {"product_name": "Server", "region_name": "South Asia", "total_revenue": 630000.0, "total_profit": 255000.0, "total_quantity": 150},
    {"product_name": "Server", "region_name": "Western Europe", "total_revenue": 504000.0, "total_profit": 204000.0, "total_quantity": 120},
]

_CUSTOMER_PURCHASE_HISTORY = [
    {"customer_name": "Customer_042", "sale_date": "2026-08-18", "product_name": "Smartphone", "quantity": 12, "revenue": 8388.0, "profit": 4188.0},
    {"customer_name": "Customer_042", "sale_date": "2026-07-09", "product_name": "Server", "quantity": 2, "revenue": 8400.0, "profit": 3400.0},
    {"customer_name": "Customer_178", "sale_date": "2026-08-11", "product_name": "Storage NAS", "quantity": 5, "revenue": 7250.0, "profit": 3250.0},
    {"customer_name": "Customer_178", "sale_date": "2026-06-22", "product_name": "Firewall Appliance", "quantity": 3, "revenue": 3600.0, "profit": 2100.0},
    {"customer_name": "Customer_005", "sale_date": "2026-08-03", "product_name": "Projector", "quantity": 4, "revenue": 3800.0, "profit": 1800.0},
]

_LOW_MARGIN_PRODUCTS = [
    {"product_id": 2, "product_name": "Server", "category": "Infrastructure", "total_revenue": 3780000.0, "total_profit": 1530000.0, "profit_margin_pct": 40.48},
    {"product_id": 3, "product_name": "Storage NAS", "category": "Infrastructure", "total_revenue": 1595000.0, "total_profit": 715000.0, "profit_margin_pct": 44.83},
    {"product_id": 6, "product_name": "Projector", "category": "Electronics", "total_revenue": 855000.0, "total_profit": 405000.0, "profit_margin_pct": 47.37},
    {"product_id": 1, "product_name": "Smartphone", "category": "Electronics", "total_revenue": 3634800.0, "total_profit": 1814800.0, "profit_margin_pct": 49.93},
]

_MONTH_OVER_MONTH_GROWTH = [
    {"month": "2026-01-01", "total_revenue": 620000.0, "total_profit": 223200.0, "previous_revenue": None, "revenue_growth_pct": None},
    {"month": "2026-02-01", "total_revenue": 655000.0, "total_profit": 235800.0, "previous_revenue": 620000.0, "revenue_growth_pct": 5.65},
    {"month": "2026-03-01", "total_revenue": 690000.0, "total_profit": 248400.0, "previous_revenue": 655000.0, "revenue_growth_pct": 5.34},
    {"month": "2026-04-01", "total_revenue": 725000.0, "total_profit": 261000.0, "previous_revenue": 690000.0, "revenue_growth_pct": 5.07},
    {"month": "2026-05-01", "total_revenue": 760000.0, "total_profit": 273600.0, "previous_revenue": 725000.0, "revenue_growth_pct": 4.83},
    {"month": "2026-06-01", "total_revenue": 800000.0, "total_profit": 288000.0, "previous_revenue": 760000.0, "revenue_growth_pct": 5.26},
]

_REPEAT_CUSTOMER_SUMMARY = [
    {"region_name": "East Asia", "customer_count": 34, "repeat_customer_count": 22},
    {"region_name": "Western Europe", "customer_count": 29, "repeat_customer_count": 17},
    {"region_name": "Oceania", "customer_count": 27, "repeat_customer_count": 15},
]


def _fake_get_top_products(limit=5, region=None):
    data = _EAST_ASIA_PRODUCTS if region == "East Asia" else _ALL_PRODUCTS
    return data[:limit]


def _fake_get_top_customers(limit=5, region=None):
    data = _EAST_ASIA_CUSTOMERS if region == "East Asia" else _ALL_CUSTOMERS
    return data[:limit]


def _fake_get_region_performance():
    return _REGIONS


def _fake_get_sales_trend(period="month", region=None):
    return _TREND


def _fake_get_profit_analysis(dimension="product"):
    return _PROFIT_BY_DIMENSION.get(dimension, _PROFIT_BY_DIMENSION["product"])


def _fake_get_summary_kpi(date_from=None, date_to=None):
    return _SUMMARY_KPI


def _filter_region(rows, region):
    if region is None:
        return rows
    return [row for row in rows if row.get("region_name") == region]


def _fake_top_products_by_quantity(limit=5, region=None, date_from=None, date_to=None):
    if region == "East Asia":
        return [
            {"product_id": row["product_id"], "product_name": row["product_name"], "category": row["category"],
             "total_quantity": row["total_quantity"], "total_revenue": row["total_revenue"]}
            for row in _EAST_ASIA_PRODUCTS
        ][:limit]
    return _ANALYTICS_PRODUCTS_BY_QUANTITY[:limit]


def _fake_top_products_by_profit(limit=5, region=None, date_from=None, date_to=None):
    if region == "East Asia":
        return [
            {"product_id": row["product_id"], "product_name": row["product_name"], "category": row["category"],
             "total_profit": row["total_profit"], "total_revenue": row["total_revenue"],
             "profit_margin_pct": round(row["total_profit"] / row["total_revenue"] * 100, 2)}
            for row in _EAST_ASIA_PRODUCTS
        ][:limit]
    return _ANALYTICS_PRODUCTS_BY_PROFIT[:limit]


def _fake_category_performance(region=None, date_from=None, date_to=None):
    return _CATEGORY_PERFORMANCE


def _fake_segment_performance(region=None, date_from=None, date_to=None):
    return _SEGMENT_PERFORMANCE


def _fake_product_region_performance(product_name=None, region=None, date_from=None, date_to=None):
    return [
        row for row in _PRODUCT_REGION_PERFORMANCE
        if (product_name is None or row["product_name"] == product_name)
        and (region is None or row["region_name"] == region)
    ]


def _fake_customer_purchase_history(customer_name, date_from=None, date_to=None):
    search = customer_name.casefold()
    return [row for row in _CUSTOMER_PURCHASE_HISTORY if search in row["customer_name"].casefold()]


def _fake_low_margin_products(limit=5, region=None, date_from=None, date_to=None):
    if region == "East Asia":
        return [
            {"product_id": row["product_id"], "product_name": row["product_name"], "category": row["category"],
             "total_revenue": row["total_revenue"], "total_profit": row["total_profit"],
             "profit_margin_pct": round(row["total_profit"] / row["total_revenue"] * 100, 2)}
            for row in reversed(_EAST_ASIA_PRODUCTS)
        ][:limit]
    return _LOW_MARGIN_PRODUCTS[:limit]


def _fake_month_over_month_growth(region=None):
    return _MONTH_OVER_MONTH_GROWTH


def _fake_repeat_customer_summary(region=None):
    return _filter_region(_REPEAT_CUSTOMER_SUMMARY, region)


def _fake_sales_range(*args, **kwargs):
    return {"order_count": 570, "total_quantity": 854, "total_revenue": 8500000.0,
            "total_profit": 3110000.0, "profit_margin_pct": 36.59}


def _fake_check_connection():
    return True


def apply_fakes() -> None:
    product_dao.get_top_products = _fake_get_top_products
    customer_dao.get_top_customers = _fake_get_top_customers
    region_dao.get_region_performance = _fake_get_region_performance
    sales_dao.get_sales_trend = _fake_get_sales_trend
    sales_dao.get_profit_analysis = _fake_get_profit_analysis
    sales_dao.get_summary_kpi = _fake_get_summary_kpi
    analytics_dao.get_top_products_by_quantity = _fake_top_products_by_quantity
    analytics_dao.get_top_products_by_profit = _fake_top_products_by_profit
    analytics_dao.get_category_performance = _fake_category_performance
    analytics_dao.get_segment_performance = _fake_segment_performance
    analytics_dao.get_product_region_performance = _fake_product_region_performance
    analytics_dao.get_customer_purchase_history = _fake_customer_purchase_history
    analytics_dao.get_low_margin_products = _fake_low_margin_products
    analytics_dao.get_month_over_month_growth = _fake_month_over_month_growth
    analytics_dao.get_repeat_customer_summary = _fake_repeat_customer_summary
    analytics_dao.get_sales_by_date_range = _fake_sales_range
    connection_pool.check_connection = _fake_check_connection

    # Dynamic-SQL agent path (answer_with_sql/sql_db_schema) - bypasses
    # database.dao entirely, so it needs a real queryable database, not a
    # monkeypatched function. Always registered on the agent regardless
    # of FIXED_TOOLS_ENABLED, so this engine is always exercised.
    fake_sql_engine = build_fake_sql_engine()
    sql_db.engine = fake_sql_engine
    sql_db.readonly_engine = fake_sql_engine
    sql_db.get_sql_database.cache_clear()
    sql_db.get_execution_sql_database.cache_clear()


if __name__ == "__main__":
    apply_fakes()
    from config.settings import is_fixed_tools_enabled

    print("answer_with_sql/sql_db_schema are always registered and will run against the fake in-memory SQLite database.")
    if is_fixed_tools_enabled():
        print("FIXED_TOOLS_ENABLED=true (default) - the 16 fixed business tools are also registered.")
    else:
        print("FIXED_TOOLS_ENABLED=false - only the dynamic-SQL tools are registered. "
              "Set FIXED_TOOLS_ENABLED=true in .env (or the frontend's runtime toggle) to also exercise the fixed business tools.")

    from app import app  # import after patching, so any DB-touching code at import time is already faked

    import os
    from urllib.parse import urlparse
    backend_url = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
    try:
        port = urlparse(backend_url).port or 8000
    except Exception:
        port = 8000
    uvicorn.run(app, host="127.0.0.1", port=port)

