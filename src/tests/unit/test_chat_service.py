from types import SimpleNamespace

from backend.models.message import Message
from backend.services import chat_service
from tests.unit.helpers import FakeExecutor


def test_handle_message_persists_user_assistant_and_tool_results(monkeypatch):
    conversation_id = "unit-chat"
    chat_service.reset_conversation(conversation_id)
    executor = FakeExecutor({"output": "Answer", "intermediate_steps": []})
    monkeypatch.setattr(chat_service, "_agent_executor", executor)
    monkeypatch.setattr(chat_service, "_agent_executor_fixed_tools_enabled", chat_service.is_fixed_tools_enabled())
    monkeypatch.setattr("langchain_app.agent.OOS_ENABLED", False)

    result = chat_service.handle_message(conversation_id, "Show revenue")
    conversation = chat_service.get_conversation(conversation_id)

    assert result == {"answer": "Answer", "source_tables": [], "kb_chunks": [], "chart_data": None}
    assert [message.role for message in conversation.messages] == ["user", "assistant"]
    assert conversation.messages[1].content == "Answer"
    assert conversation.messages[1].tool_results == []
    assert executor.calls[0]["chat_history"] == []


def test_handle_message_passes_previous_turns_as_history(monkeypatch):
    conversation_id = "unit-follow-up"
    chat_service.reset_conversation(conversation_id)
    executor = FakeExecutor({"output": "Follow-up answer", "intermediate_steps": []})
    monkeypatch.setattr(chat_service, "_agent_executor", executor)
    monkeypatch.setattr(chat_service, "_agent_executor_fixed_tools_enabled", chat_service.is_fixed_tools_enabled())
    monkeypatch.setattr("langchain_app.agent.OOS_ENABLED", False)

    chat_service.handle_message(conversation_id, "Show revenue")
    chat_service.handle_message(conversation_id, "Only in Asia")

    history = executor.calls[1]["chat_history"]
    assert [message.content for message in history] == ["Show revenue", "Follow-up answer"]


def test_handle_message_persists_and_returns_chart_data(monkeypatch):
    conversation_id = "unit-chart"
    chat_service.reset_conversation(conversation_id)
    steps = [
        (
            SimpleNamespace(tool="get_sales_trend", tool_input={"period": "month"}),
            {"trend": [{"period": "2025-01", "total_revenue": 1000}], "period": "month", "region": None},
        )
    ]
    executor = FakeExecutor({"output": "Here's the trend", "intermediate_steps": steps})
    monkeypatch.setattr(chat_service, "_agent_executor", executor)
    monkeypatch.setattr(chat_service, "_agent_executor_fixed_tools_enabled", chat_service.is_fixed_tools_enabled())
    monkeypatch.setattr("langchain_app.agent.OOS_ENABLED", False)

    result = chat_service.handle_message(conversation_id, "Show sales trend")
    conversation = chat_service.get_conversation(conversation_id)

    assert result["chart_data"] == [{"x": "2025-01", "y": 1000}]
    assert conversation.messages[1].chart_data == [{"x": "2025-01", "y": 1000}]


def test_get_agent_executor_rebuilds_when_fixed_tools_flag_changes(monkeypatch):
    """The frontend's runtime toggle (settings_controller.set_fixed_tools_enabled)
    must invalidate the cached executor - otherwise the demo flips the flag
    and nothing changes until the backend is restarted."""
    stale_executor = FakeExecutor({"output": "stale", "intermediate_steps": []})
    fresh_executor = FakeExecutor({"output": "fresh", "intermediate_steps": []})
    build_calls = []
    monkeypatch.setattr(chat_service, "_agent_executor", stale_executor)
    monkeypatch.setattr(chat_service, "_agent_executor_fixed_tools_enabled", True)
    monkeypatch.setattr(chat_service, "is_fixed_tools_enabled", lambda: False)
    monkeypatch.setattr(
        chat_service, "build_agent_executor", lambda: build_calls.append(1) or fresh_executor
    )

    assert chat_service._get_agent_executor() is fresh_executor
    assert chat_service._agent_executor_fixed_tools_enabled is False
    # A second call with no further flag change reuses the rebuilt executor
    # instead of rebuilding again.
    assert chat_service._get_agent_executor() is fresh_executor
    assert len(build_calls) == 1


def test_reset_conversation_removes_history():
    conversation_id = "unit-reset"
    chat_service.reset_conversation(conversation_id)
    chat_service.get_conversation(conversation_id).add_message(Message(role="user", content="Hello"))

    chat_service.reset_conversation(conversation_id)

    assert chat_service.get_conversation(conversation_id).messages == []