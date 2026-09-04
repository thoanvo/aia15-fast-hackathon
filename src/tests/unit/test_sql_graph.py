from dataclasses import dataclass
from decimal import Decimal

from langchain_app import sql_graph


@dataclass
class FakeResponse:
    content: str


class FakeLlm:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = []

    def invoke(self, messages):
        self.calls.append(messages[0].content)
        return FakeResponse(self.responses.pop(0))


class FakeRow:
    def __init__(self, mapping):
        self._mapping = mapping


class FakeExecutionDatabase:
    def __init__(self, rows=None, error=None):
        self.rows = rows or []
        self.error = error
        self.run_calls = []

    def run(self, query, fetch=None):
        self.run_calls.append(query)
        if self.error:
            raise self.error
        return [FakeRow(r) for r in self.rows]


def test_discover_schema_sets_context_from_question(monkeypatch):
    monkeypatch.setattr(sql_graph, "build_sql_generation_context", lambda question: f"context-for:{question}")

    result = sql_graph.discover_schema({"question": "top products?"})

    assert result == {"schema_context": "context-for:top products?"}


def test_generate_sql_calls_llm_and_strips_code_fence():
    fake_llm = FakeLlm(["```sql\nSELECT * FROM sales\n```"])

    result = sql_graph.generate_sql(
        {"question": "q", "schema_context": "ctx", "error": None, "attempt": 0}, llm=fake_llm
    )

    assert result == {"generated_sql": "SELECT * FROM sales", "attempt": 1, "error": None}
    assert "q" in fake_llm.calls[0]
    assert "ctx" in fake_llm.calls[0]


def test_generate_sql_includes_previous_error_in_retry_prompt():
    fake_llm = FakeLlm(["SELECT 1"])

    sql_graph.generate_sql(
        {"question": "q", "schema_context": "ctx", "error": "column x does not exist", "attempt": 1}, llm=fake_llm
    )

    assert "column x does not exist" in fake_llm.calls[0]


def test_validate_sql_returns_checked_query_on_success(monkeypatch):
    monkeypatch.setattr(sql_graph, "validate_select_only", lambda q: f"{q} LIMIT 100")

    result = sql_graph.validate_sql({"generated_sql": "SELECT * FROM sales"})

    assert result == {"generated_sql": "SELECT * FROM sales LIMIT 100", "error": None}


def test_validate_sql_returns_error_on_rejection(monkeypatch):
    def reject(q):
        raise ValueError("only SELECT statements are allowed")

    monkeypatch.setattr(sql_graph, "validate_select_only", reject)

    result = sql_graph.validate_sql({"generated_sql": "DELETE FROM sales"})

    assert result == {"error": "only SELECT statements are allowed"}


def test_execute_sql_returns_rows_on_success(monkeypatch):
    fake_db = FakeExecutionDatabase(rows=[{"total": 100}])
    monkeypatch.setattr(sql_graph, "get_execution_sql_database", lambda: fake_db)

    result = sql_graph.execute_sql({"generated_sql": "SELECT SUM(revenue) AS total FROM sales"})

    assert result == {"rows": [{"total": 100}], "error": None}
    assert fake_db.run_calls == ["SELECT SUM(revenue) AS total FROM sales"]


def test_execute_sql_normalizes_decimal_aggregates_to_float(monkeypatch):
    """Postgres SUM()/AVG() aggregates come back as decimal.Decimal, which
    chart_data.extract_chart_data()'s numeric check doesn't recognize -
    un-normalized, this made every answer_with_sql result look
    non-chart-worthy (see chart_data.py's _pick_columns numeric check)."""
    fake_db = FakeExecutionDatabase(rows=[{"product_name": "Laptop", "total_revenue": Decimal("1234.50")}])
    monkeypatch.setattr(sql_graph, "get_execution_sql_database", lambda: fake_db)

    result = sql_graph.execute_sql(
        {"generated_sql": "SELECT product_name, SUM(revenue) AS total_revenue FROM sales GROUP BY product_name"}
    )

    assert result == {"rows": [{"product_name": "Laptop", "total_revenue": 1234.5}], "error": None}
    assert isinstance(result["rows"][0]["total_revenue"], float)


def test_execute_sql_returns_error_on_database_failure(monkeypatch):
    fake_db = FakeExecutionDatabase(error=RuntimeError("column does not exist"))
    monkeypatch.setattr(sql_graph, "get_execution_sql_database", lambda: fake_db)

    result = sql_graph.execute_sql({"generated_sql": "SELECT bad_column FROM sales"})

    assert result == {"error": "column does not exist"}


def test_after_validate_routes_to_execute_when_no_error():
    assert sql_graph._after_validate({"error": None, "attempt": 1}) == "execute"


def test_after_validate_routes_to_retry_under_cap(monkeypatch):
    monkeypatch.setattr(sql_graph, "SQL_AGENT_MAX_RETRIES", 3)

    assert sql_graph._after_validate({"error": "bad", "attempt": 1}) == "retry"


def test_after_validate_gives_up_at_cap(monkeypatch):
    monkeypatch.setattr(sql_graph, "SQL_AGENT_MAX_RETRIES", 3)

    assert sql_graph._after_validate({"error": "bad", "attempt": 3}) == "give_up"


def test_full_graph_retries_generation_after_validation_failure_then_succeeds(monkeypatch):
    monkeypatch.setattr(sql_graph, "build_sql_generation_context", lambda question: "SCHEMA")
    monkeypatch.setattr(sql_graph, "SQL_AGENT_MAX_RETRIES", 3)

    call_count = {"validate": 0}

    def validate_fails_once_then_succeeds(query):
        call_count["validate"] += 1
        if call_count["validate"] == 1:
            raise ValueError("only SELECT statements are allowed")
        return query

    monkeypatch.setattr(sql_graph, "validate_select_only", validate_fails_once_then_succeeds)
    fake_db = FakeExecutionDatabase(rows=[{"total_revenue": 500}])
    monkeypatch.setattr(sql_graph, "get_execution_sql_database", lambda: fake_db)
    fake_llm = FakeLlm(["DELETE FROM sales", "SELECT SUM(revenue) AS total_revenue FROM sales"])

    final_state = sql_graph.run_sql_graph("What is total revenue?", llm=fake_llm)

    assert final_state["error"] is None
    assert final_state["rows"] == [{"total_revenue": 500}]
    assert final_state["attempt"] == 2
    assert len(fake_llm.calls) == 2


def test_full_graph_gives_up_after_max_retries(monkeypatch):
    monkeypatch.setattr(sql_graph, "build_sql_generation_context", lambda question: "SCHEMA")
    monkeypatch.setattr(sql_graph, "SQL_AGENT_MAX_RETRIES", 2)

    def always_reject(query):
        raise ValueError("bad query")

    monkeypatch.setattr(sql_graph, "validate_select_only", always_reject)
    fake_llm = FakeLlm(["SELECT 1", "SELECT 2", "SELECT 3"])

    final_state = sql_graph.run_sql_graph("An unanswerable question", llm=fake_llm)

    assert final_state["error"] == "bad query"
    assert final_state["rows"] is None
    assert final_state["attempt"] == 2


def test_full_graph_retries_after_execution_failure_then_succeeds(monkeypatch):
    monkeypatch.setattr(sql_graph, "build_sql_generation_context", lambda question: "SCHEMA")
    monkeypatch.setattr(sql_graph, "SQL_AGENT_MAX_RETRIES", 3)
    monkeypatch.setattr(sql_graph, "validate_select_only", lambda q: q)

    call_count = {"execute": 0}

    class FlakyDatabase:
        def run(self, query, fetch=None):
            call_count["execute"] += 1
            if call_count["execute"] == 1:
                raise RuntimeError("column bad_col does not exist")
            return [FakeRow({"total_revenue": 500})]

    monkeypatch.setattr(sql_graph, "get_execution_sql_database", lambda: FlakyDatabase())
    fake_llm = FakeLlm(["SELECT bad_col FROM sales", "SELECT SUM(revenue) AS total_revenue FROM sales"])

    final_state = sql_graph.run_sql_graph("What is total revenue?", llm=fake_llm)

    assert final_state["error"] is None
    assert final_state["rows"] == [{"total_revenue": 500}]
