from datetime import date
from decimal import Decimal

import pytest

from database.connection import connection_pool
from database.dao import product_dao, sales_dao


class FakeMappings:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows

    def first(self):
        return self.rows[0] if self.rows else None


class FakeResult:
    def __init__(self, rows):
        self.rows = rows

    def mappings(self):
        return FakeMappings(self.rows)


class FakeSession:
    def __init__(self, rows):
        self.rows = rows
        self.calls = []

    def execute(self, statement, parameters=None):
        self.calls.append((str(statement), parameters))
        return FakeResult(self.rows)


class SessionContext:
    def __init__(self, session):
        self.session = session

    def __enter__(self):
        return self.session

    def __exit__(self, exc_type, exc_value, traceback):
        return False


def test_serialize_row_normalizes_decimal_and_dates():
    result = connection_pool.serialize_row(
        {"amount": Decimal("12.50"), "sale_date": date(2025, 1, 2), "name": "Laptop"}
    )

    assert result == {"amount": 12.5, "sale_date": "2025-01-02", "name": "Laptop"}


def test_get_top_products_forwards_limit_and_region(monkeypatch):
    session = FakeSession([{"product_name": "Laptop", "total_revenue": Decimal("100") }])
    monkeypatch.setattr(product_dao, "get_session", lambda: SessionContext(session))

    result = product_dao.get_top_products(limit=3, region="Asia")

    assert result == [{"product_name": "Laptop", "total_revenue": 100.0}]
    assert session.calls[0][1] == {"limit": 3, "region": "Asia"}


def test_sales_trend_rejects_unsupported_period_before_database_call():
    with pytest.raises(ValueError, match="Unsupported period"):
        sales_dao.get_sales_trend(period="quarter")


def test_get_summary_kpi_returns_empty_dict_for_no_rows(monkeypatch):
    session = FakeSession([])
    monkeypatch.setattr(sales_dao, "get_session", lambda: SessionContext(session))

    assert sales_dao.get_summary_kpi("2025-01-01", "2025-01-31") == {}
    assert session.calls[0][1] == {"date_from": "2025-01-01", "date_to": "2025-01-31"}