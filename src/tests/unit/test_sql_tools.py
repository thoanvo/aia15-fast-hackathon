from langchain_app.tools import sql_tools


class FakeSQLDatabase:
    def __init__(self, schema_text=""):
        self.schema_text = schema_text
        self.schema_calls = []

    def get_table_info(self, table_names=None):
        self.schema_calls.append(table_names)
        return self.schema_text


def test_sql_db_schema_returns_fake_schema_text(monkeypatch):
    fake = FakeSQLDatabase(schema_text="CREATE TABLE sales (...)")
    monkeypatch.setattr(sql_tools, "get_sql_database", lambda: fake)

    result = sql_tools.sql_db_schema.invoke({"table_names": "sales, products"})

    assert result == "CREATE TABLE sales (...)"
    assert fake.schema_calls == [["sales", "products"]]


def test_answer_with_sql_returns_rows_and_query_on_success(monkeypatch):
    monkeypatch.setattr(
        sql_tools,
        "run_sql_graph",
        lambda question: {"error": None, "rows": [{"total_revenue": 100}], "generated_sql": "SELECT 1"},
    )

    result = sql_tools.answer_with_sql.invoke({"question": "What is total revenue?"})

    assert result == {"rows": [{"total_revenue": 100}], "query": "SELECT 1"}


def test_answer_with_sql_returns_error_when_graph_gives_up(monkeypatch):
    monkeypatch.setattr(
        sql_tools,
        "run_sql_graph",
        lambda question: {"error": "column bad_col does not exist", "rows": None, "generated_sql": "SELECT bad_col FROM sales"},
    )

    result = sql_tools.answer_with_sql.invoke({"question": "An unanswerable question"})

    assert result == {"error": "column bad_col does not exist"}


def test_answer_with_sql_returns_error_when_graph_raises(monkeypatch):
    def fail(question):
        raise RuntimeError("graph construction failed")

    monkeypatch.setattr(sql_tools, "run_sql_graph", fail)

    result = sql_tools.answer_with_sql.invoke({"question": "anything"})

    assert result == {"error": "graph construction failed"}


def test_get_sql_tools_returns_both_tools():
    tools = sql_tools.get_sql_tools()

    assert [t.name for t in tools] == ["sql_db_schema", "answer_with_sql"]
