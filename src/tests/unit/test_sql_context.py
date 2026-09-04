from types import SimpleNamespace

from langchain_app import sql_context


class FakeSQLDatabase:
    def __init__(self, table_info):
        self.table_info = table_info

    def get_table_info(self):
        return self.table_info


class FakeRetriever:
    def __init__(self, docs):
        self.docs = docs
        self.calls = []

    def invoke(self, query):
        self.calls.append(query)
        return self.docs


def test_structural_floor_returns_live_schema_text(monkeypatch):
    monkeypatch.setattr(sql_context, "get_sql_database", lambda: FakeSQLDatabase("CREATE TABLE sales (...)"))

    assert sql_context._structural_floor() == "CREATE TABLE sales (...)"


def test_structural_floor_falls_back_when_database_unreachable(monkeypatch):
    def fail_get_sql_database():
        raise RuntimeError("connection refused")

    monkeypatch.setattr(sql_context, "get_sql_database", fail_get_sql_database)

    assert sql_context._structural_floor() == sql_context._SCHEMA_UNAVAILABLE_MESSAGE


def test_retrieved_business_context_joins_document_content(monkeypatch):
    docs = [SimpleNamespace(page_content="Table: sales business rules"), SimpleNamespace(page_content="Metric: margin")]
    fake_retriever = FakeRetriever(docs)
    monkeypatch.setattr(sql_context, "get_retriever", lambda k: fake_retriever)

    result = sql_context._retrieved_business_context("What is profit margin?")

    assert result == "Table: sales business rules\n\nMetric: margin"
    assert fake_retriever.calls == ["What is profit margin?"]


def test_retrieved_business_context_returns_empty_on_no_docs(monkeypatch):
    monkeypatch.setattr(sql_context, "get_retriever", lambda k: FakeRetriever([]))

    assert sql_context._retrieved_business_context("anything") == ""


def test_retrieved_business_context_returns_empty_on_retrieval_failure(monkeypatch):
    def fail_get_retriever(k):
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(sql_context, "get_retriever", fail_get_retriever)

    assert sql_context._retrieved_business_context("anything") == ""


def test_build_sql_generation_context_combines_structural_floor_and_retrieved_context(monkeypatch):
    monkeypatch.setattr(sql_context, "_structural_floor", lambda: "STRUCTURAL")
    monkeypatch.setattr(sql_context, "_retrieved_business_context", lambda question: "RETRIEVED")

    result = sql_context.build_sql_generation_context("some question")

    assert result == "STRUCTURAL\n\nRelevant business context:\nRETRIEVED"


def test_build_sql_generation_context_omits_business_context_section_when_nothing_retrieved(monkeypatch):
    monkeypatch.setattr(sql_context, "_structural_floor", lambda: "STRUCTURAL")
    monkeypatch.setattr(sql_context, "_retrieved_business_context", lambda question: "")

    result = sql_context.build_sql_generation_context("some question")

    assert result == "STRUCTURAL"
