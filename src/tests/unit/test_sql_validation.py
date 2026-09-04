import pytest

from langchain_app import sql_validation
from langchain_app.sql_validation import SQLValidationError, validate_select_only


def test_accepts_plain_select_unchanged():
    assert validate_select_only("SELECT * FROM sales LIMIT 10") == "SELECT * FROM sales LIMIT 10"


def test_accepts_cte_select():
    query = "WITH monthly AS (SELECT 1 AS x) SELECT * FROM monthly"
    result = validate_select_only(query)

    assert result.startswith("WITH monthly AS (SELECT 1 AS x) SELECT * FROM monthly")
    assert "LIMIT 100" in result


def test_rejects_stacked_statement():
    with pytest.raises(SQLValidationError, match="single SQL statement"):
        validate_select_only("SELECT 1; DROP TABLE sales;")


def test_rejects_delete():
    with pytest.raises(SQLValidationError, match="Only SELECT statements are allowed"):
        validate_select_only("DELETE FROM sales")


def test_rejects_two_select_statements():
    with pytest.raises(SQLValidationError, match="single SQL statement"):
        validate_select_only("SELECT * FROM sales; SELECT * FROM products")


def test_appends_limit_when_missing():
    assert validate_select_only("SELECT * FROM sales") == "SELECT * FROM sales LIMIT 100"


def test_rewrites_limit_above_cap():
    assert validate_select_only("SELECT * FROM sales LIMIT 5000") == "SELECT * FROM sales LIMIT 100"


def test_leaves_limit_under_cap_unchanged():
    assert validate_select_only("SELECT * FROM sales LIMIT 50") == "SELECT * FROM sales LIMIT 50"


def test_max_rows_setting_is_respected(monkeypatch):
    monkeypatch.setattr(sql_validation, "SQL_AGENT_MAX_ROWS", 10)

    assert validate_select_only("SELECT * FROM sales") == "SELECT * FROM sales LIMIT 10"
