"""Database Layer - Init DB script.

Runs schema.sql then mock_data/sample_data.sql against the configured
Neon PostgreSQL database, and verifies the row counts afterwards.

Usage (from src/):
    python database/scripts/init_db.py
"""

import sys
from pathlib import Path

SRC_ROOT = Path(__file__).resolve().parents[2]
if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))

from sqlalchemy import create_engine, text  # noqa: E402

from config.settings import DATABASE_URL  # noqa: E402

SCRIPTS_DIR = Path(__file__).resolve().parent
MOCK_DATA_DIR = SCRIPTS_DIR.parent / "mock_data"
TABLES = ["regions", "products", "customers", "sales"]


def _run_sql_file(conn, path: Path) -> None:
    sql = path.read_text(encoding="utf-8")
    conn.exec_driver_sql(sql)


def main() -> None:
    engine = create_engine(DATABASE_URL)

    with engine.begin() as conn:
        schema_path = SCRIPTS_DIR / "schema.sql"
        print(f"Running {schema_path} ...")
        _run_sql_file(conn, schema_path)

        data_path = MOCK_DATA_DIR / "sample_data.sql"
        print(f"Running {data_path} ...")
        _run_sql_file(conn, data_path)

    print("\nRow counts:")
    with engine.connect() as conn:
        for table in TABLES:
            count = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar()
            print(f"  {table}: {count}")


if __name__ == "__main__":
    main()
