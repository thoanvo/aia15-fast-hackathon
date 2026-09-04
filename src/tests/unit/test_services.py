from backend.models.conversation import Conversation
from backend.models.message import Message
from backend.services import insight_service, recommendation_service
from tests.unit.helpers import FakeLlm


def test_insight_without_tool_results_returns_guard_message():
    assert insight_service.generate_business_insight(Conversation(id="empty"), "Give insights") == (
        insight_service.NO_DATA_MESSAGE
    )


def test_insight_uses_latest_tool_result(monkeypatch):
    conversation = Conversation(id="with-data")
    conversation.add_message(
        Message(
            role="assistant",
            content="Answer",
            tool_results=[{"tool": "get_top_products", "result": {"product": "Laptop"}}],
        )
    )
    fake_llm = FakeLlm("Insight")
    monkeypatch.setattr(insight_service, "get_llm", lambda: fake_llm)

    result = insight_service.generate_business_insight(conversation, "What matters?")

    assert result == "Insight"
    prompt = fake_llm.calls[0][0].content
    assert "What matters?" in prompt
    assert "get_top_products" in prompt
    assert "Laptop" in prompt


def test_insight_uses_latest_tool_result_from_dynamic_sql_path(monkeypatch):
    """generate_business_insight() is generic over tool_results' shape -
    a run_sql_query result ({"rows": [...], "query": "..."}) needs no
    special-casing, same code path as a fixed business tool's result."""
    conversation = Conversation(id="with-sql-data")
    conversation.add_message(
        Message(
            role="assistant",
            content="Answer",
            tool_results=[
                {
                    "tool": "run_sql_query",
                    "args": {"query": "SELECT category, SUM(revenue) FROM sales GROUP BY category"},
                    "result": {
                        "rows": [{"category": "Electronics", "sum": 1000}, {"category": "Accessories", "sum": 500}],
                        "query": "SELECT category, SUM(revenue) FROM sales GROUP BY category LIMIT 100",
                    },
                }
            ],
        )
    )
    fake_llm = FakeLlm("Insight")
    monkeypatch.setattr(insight_service, "get_llm", lambda: fake_llm)

    result = insight_service.generate_business_insight(conversation, "What matters?")

    assert result == "Insight"
    prompt = fake_llm.calls[0][0].content
    assert "run_sql_query" in prompt
    assert "Electronics" in prompt


def test_recommendation_uses_insight(monkeypatch):
    fake_llm = FakeLlm("Recommendation")
    monkeypatch.setattr(recommendation_service, "get_llm", lambda: fake_llm)

    result = recommendation_service.generate_recommendation("Asia leads revenue")

    assert result == "Recommendation"
    assert "Asia leads revenue" in fake_llm.calls[0][0].content