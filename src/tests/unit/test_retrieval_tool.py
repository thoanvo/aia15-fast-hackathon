from types import SimpleNamespace

from langchain_app.tools import retrieval_tool


def test_search_knowledge_base_formats_documents_and_requests_three_results(monkeypatch):
    calls = []

    class FakeRetriever:
        def invoke(self, query):
            calls.append(query)
            return [
                SimpleNamespace(
                    metadata={"source": "schema.md", "title": "Sales"},
                    page_content="Sales columns",
                ),
                SimpleNamespace(metadata={}, page_content="SQL example"),
            ]

    def fake_get_retriever(k):
        assert k == 3
        return FakeRetriever()

    monkeypatch.setattr(retrieval_tool, "get_retriever", fake_get_retriever)

    result = retrieval_tool.search_knowledge_base.invoke({"query": "How is revenue stored?"})

    assert calls == ["How is revenue stored?"]
    assert "[schema.md > Sales]\nSales columns" in result
    assert "[unknown > ]\nSQL example" in result
    assert "\n\n---\n\n" in result


def test_search_knowledge_base_handles_empty_results(monkeypatch):
    monkeypatch.setattr(retrieval_tool, "get_retriever", lambda k: SimpleNamespace(invoke=lambda query: []))

    assert retrieval_tool.search_knowledge_base.invoke({"query": "unknown"}) == (
        "No relevant knowledge-base content found."
    )


def test_search_knowledge_base_handles_retrieval_failure(monkeypatch):
    def fail_get_retriever(k):
        raise RuntimeError("index unavailable")

    monkeypatch.setattr(retrieval_tool, "get_retriever", fail_get_retriever)

    assert retrieval_tool.search_knowledge_base.invoke({"query": "schema"}) == (
        "Knowledge-base search failed: index unavailable"
    )