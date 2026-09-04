"""DEV-ONLY: an in-memory SQLite engine standing in for the real Postgres
database, specifically for exercising the dynamic-SQL agent path
(langchain_app.sql_db / sql_graph / sql_tools.answer_with_sql) without a
reachable Postgres instance.

dev_fake_backend.py's own DAO-level monkeypatching (apply_fakes()) only
covers the 16 fixed business tools (business_tools.py -> database.dao.*).
It does nothing for answer_with_sql / sql_db_schema, which talk directly
to a real SQLAlchemy engine (sql_db.py) for schema reflection and query
execution - the LLM generates arbitrary SQL, so unlike the DAO layer
there's no fixed set of Python functions to swap out; a real, queryable
database is the only thing that can stand in. This module builds one:
same schema shape as database/scripts/schema.sql, with the DDL adapted
to SQLite.

Seed data: regions/products are reused verbatim from
database/mock_data/sample_data.sql (plain INSERT ... VALUES syntax is
portable). customers/sales in that file are instead generated with
Postgres-only SQL (generate_series, ::int casts, DATE '...' literals) to
produce a large randomized demo-staging dataset - not portable to
SQLite, so those two statements are skipped when reading the file and
replaced with `_SQLITE_CUSTOMERS_SEED`/`_SQLITE_SALES_SEED` below: a
SQLite-native equivalent (recursive CTE standing in for generate_series,
a registered `rand_frac()` function standing in for a 0-1 random()
float, `CAST(... AS INTEGER)` standing in for floor()) producing the
same shape - ~300 customers, ~12% of the customers x products cross
join as sales rows.

Not full Postgres compatibility - a best-effort shim for the SQL shapes
this project's own prompts/tools actually produce, not a general
Postgres-on-SQLite emulation layer:
- GENERATED ALWAYS AS (...) STORED, NULLIF, window functions
  (LAG() OVER (...)): all supported natively by SQLite 3.31+.
- Decimal columns are declared REAL, not NUMERIC(p,s) like the real
  schema - SQLite's NUMERIC type affinity stores a value with no
  fractional part (e.g. 1200.00) as an INTEGER, and integer/integer
  division truncates - every NULLIF-guarded margin/percentage
  calculation in this project's own idioms would silently compute 0
  against whole-number seed prices otherwise. REAL forces floating-point
  storage and division, matching Postgres NUMERIC's actual behavior.
- date_trunc(unit, date): not a SQLite function - emulated below for the
  'day'/'month'/'year' units this project's tools/prompts use. Anything
  more exotic the LLM might generate (INTERVAL, EXTRACT, Postgres-only
  casts) is not emulated and surfaces as a query execution error - same
  as any other DB error the graph's retry loop already feeds back into
  regeneration, not a new failure mode.
"""

import random
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.pool import StaticPool

_SCHEMA_DDL = """
CREATE TABLE regions (
    region_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    region_name VARCHAR(100) NOT NULL UNIQUE,
    country     VARCHAR(100) NOT NULL
);

CREATE TABLE products (
    product_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    product_name VARCHAR(150) NOT NULL,
    category     VARCHAR(100) NOT NULL,
    unit_cost    REAL NOT NULL CHECK (unit_cost >= 0),
    unit_price   REAL NOT NULL CHECK (unit_price >= 0)
);

CREATE TABLE customers (
    customer_id   INTEGER PRIMARY KEY AUTOINCREMENT,
    customer_name VARCHAR(150) NOT NULL,
    segment       VARCHAR(50) NOT NULL,
    region_id     INTEGER NOT NULL REFERENCES regions(region_id)
);

CREATE TABLE sales (
    sale_id     INTEGER PRIMARY KEY AUTOINCREMENT,
    product_id  INTEGER NOT NULL REFERENCES products(product_id),
    customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
    region_id   INTEGER NOT NULL REFERENCES regions(region_id),
    sale_date   DATE NOT NULL,
    quantity    INTEGER NOT NULL CHECK (quantity > 0),
    unit_price  REAL NOT NULL CHECK (unit_price >= 0),
    unit_cost   REAL NOT NULL CHECK (unit_cost >= 0),
    revenue     REAL GENERATED ALWAYS AS (quantity * unit_price) STORED,
    profit      REAL GENERATED ALWAYS AS (quantity * (unit_price - unit_cost)) STORED
);
"""

_SEED_DATA_PATH = Path(__file__).resolve().parent / "database" / "mock_data" / "sample_data.sql"

# sample_data.sql's own customers/sales statements (skipped by
# build_fake_sql_engine() - see module docstring) - matched by table name
# so a future edit to those blocks doesn't need a matching edit here as
# long as the table name stays the first two words after "INSERT INTO".
_NON_PORTABLE_SEED_TABLES = ("INSERT INTO customers", "INSERT INTO sales")

# SQLite-native equivalents of sample_data.sql's customers/sales
# statements - see module docstring for why these can't just be the
# original Postgres SQL. `rand_frac()` (registered on connect, below)
# stands in for Postgres's random() (a 0-1 float); SQLite's own random()
# is a signed 64-bit integer, a different contract entirely.
_SQLITE_CUSTOMERS_SEED = """
WITH RECURSIVE gs(n) AS (
    SELECT 1
    UNION ALL
    SELECT n + 1 FROM gs WHERE n < 300
)
INSERT INTO customers (customer_name, segment, region_id)
SELECT
    'Customer_' || n,
    CASE
        WHEN rand_frac() < 0.4 THEN 'Enterprise'
        WHEN rand_frac() < 0.8 THEN 'SMB'
        ELSE 'Individual'
    END,
    CAST(rand_frac() * 10 + 1 AS INTEGER)
FROM gs
"""

_SQLITE_SALES_SEED = """
INSERT INTO sales (product_id, customer_id, region_id, sale_date, quantity, unit_price, unit_cost)
SELECT
    p.product_id,
    c.customer_id,
    c.region_id,
    date('2024-01-01', '+' || CAST(rand_frac() * (julianday('now') - julianday('2024-01-01')) AS INTEGER) || ' days'),
    CAST(rand_frac() * 40 + 1 AS INTEGER),
    p.unit_price,
    p.unit_cost
FROM customers c, products p
WHERE rand_frac() < 0.12
"""


def _date_trunc(unit, value):
    """Best-effort emulation of Postgres's date_trunc(unit, date) for the
    'day'/'month'/'year' units this project's own tools/prompts use."""
    if value is None:
        return None
    text = str(value)
    if unit == "year":
        return text[:4] + "-01-01"
    if unit == "month":
        return text[:7] + "-01"
    return text[:10]


def _statements(sql_text: str):
    """Split a .sql file's content into individual executable statements,
    stripping '--' comment lines first (SQLite's executemany-per-statement
    driver call doesn't accept a multi-statement script with comments the
    way psycopg2 does)."""
    for raw_statement in sql_text.split(";"):
        cleaned = "\n".join(
            line for line in raw_statement.splitlines() if not line.strip().startswith("--")
        ).strip()
        if cleaned:
            yield cleaned


def build_fake_sql_engine():
    """Build and seed an in-memory SQLite engine standing in for the real
    Postgres database, for the dynamic-SQL agent path only.

    StaticPool + check_same_thread=False: a plain ":memory:" SQLite
    database is private to the single connection that created it - the
    default connection-pooling behavior would hand out a fresh (empty)
    in-memory database per checkout. StaticPool keeps exactly one
    connection alive for the engine's lifetime so every query hits the
    same seeded database; check_same_thread=False is required for that
    one connection to be shared across FastAPI's threadpool.
    """
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def _register_functions(dbapi_connection, connection_record):
        dbapi_connection.create_function("date_trunc", 2, _date_trunc)
        dbapi_connection.create_function("rand_frac", 0, random.random)

    with engine.begin() as conn:
        for statement in _statements(_SCHEMA_DDL):
            conn.exec_driver_sql(statement)
        for statement in _statements(_SEED_DATA_PATH.read_text(encoding="utf-8")):
            if statement.startswith(_NON_PORTABLE_SEED_TABLES):
                continue
            conn.exec_driver_sql(statement)
        conn.exec_driver_sql(_SQLITE_CUSTOMERS_SEED)
        conn.exec_driver_sql(_SQLITE_SALES_SEED)

    return engine


if __name__ == "__main__":
    # Standalone sanity check only - this module has no other use running
    # directly; dev_fake_backend.py is what actually wires it into the app.
    from sqlalchemy import text

    engine = build_fake_sql_engine()
    with engine.connect() as conn:
        for table in ("regions", "products", "customers", "sales"):
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"{table}: {count} rows")

        print("\nCategory breakdown (join + GENERATED columns + NULLIF):")
        rows = conn.execute(text("""
            SELECT p.category, SUM(s.revenue) AS total_revenue, SUM(s.profit) AS total_profit,
                   ROUND(SUM(s.profit) / NULLIF(SUM(s.revenue), 0) * 100, 2) AS margin_pct
            FROM sales s JOIN products p ON s.product_id = p.product_id
            GROUP BY p.category ORDER BY total_revenue DESC
        """)).fetchall()
        for row in rows:
            print(f"  {row.category}: revenue={row.total_revenue}, profit={row.total_profit}, margin={row.margin_pct}%")

        print("\nMonthly trend (date_trunc emulation):")
        rows = conn.execute(text("""
            SELECT date_trunc('month', sale_date) AS period, SUM(revenue) AS total_revenue
            FROM sales GROUP BY period ORDER BY period
        """)).fetchall()
        for row in rows:
            print(f"  {row.period}: revenue={row.total_revenue}")

    print("\nOK - fake SQL engine built, seeded, and queryable.")
