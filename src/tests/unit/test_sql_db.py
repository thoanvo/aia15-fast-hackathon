from langchain_app import sql_db


class FakeSQLDatabase:
    def __init__(self, engine, include_tables=None):
        self.engine = engine
        self.include_tables = include_tables


def test_get_sql_database_wraps_existing_engine_with_table_allowlist(monkeypatch):
    monkeypatch.setattr(sql_db, "SQLDatabase", FakeSQLDatabase)
    sql_db.get_sql_database.cache_clear()

    result = sql_db.get_sql_database()

    assert isinstance(result, FakeSQLDatabase)
    assert result.engine is sql_db.engine
    assert result.include_tables == ["products", "customers", "regions", "sales"]

    sql_db.get_sql_database.cache_clear()


def test_get_sql_database_is_cached(monkeypatch):
    monkeypatch.setattr(sql_db, "SQLDatabase", FakeSQLDatabase)
    sql_db.get_sql_database.cache_clear()

    first = sql_db.get_sql_database()
    second = sql_db.get_sql_database()

    assert first is second

    sql_db.get_sql_database.cache_clear()


def test_get_execution_sql_database_wraps_readonly_engine_with_table_allowlist(monkeypatch):
    monkeypatch.setattr(sql_db, "SQLDatabase", FakeSQLDatabase)
    sql_db.get_execution_sql_database.cache_clear()

    result = sql_db.get_execution_sql_database()

    assert isinstance(result, FakeSQLDatabase)
    assert result.engine is sql_db.readonly_engine
    assert result.engine is not sql_db.engine
    assert result.include_tables == ["products", "customers", "regions", "sales"]

    sql_db.get_execution_sql_database.cache_clear()
