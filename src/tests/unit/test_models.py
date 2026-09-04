from langchain_core.messages import AIMessage, HumanMessage

from backend.models.conversation import Conversation
from backend.models.message import Message


def test_conversation_starts_empty_with_utc_timestamps():
    conversation = Conversation(id="conversation-1")

    assert conversation.messages == []
    assert conversation.created_at.tzinfo is not None
    assert conversation.updated_at.tzinfo is not None


def test_add_message_appends_and_updates_timestamp():
    conversation = Conversation(id="conversation-1")
    before = conversation.updated_at
    message = Message(role="user", content="Show sales")

    conversation.add_message(message)

    assert conversation.messages == [message]
    assert conversation.updated_at >= before


def test_chat_history_maps_user_and_assistant_messages():
    conversation = Conversation(id="conversation-1")
    conversation.add_message(Message(role="user", content="Show sales"))
    conversation.add_message(Message(role="assistant", content="Sales are up."))

    history = conversation.chat_history()

    assert history == [
        HumanMessage(content="Show sales"),
        AIMessage(content="Sales are up."),
    ]


def test_last_tool_results_returns_latest_assistant_tool_results():
    conversation = Conversation(id="conversation-1")
    first_results = [{"tool": "get_summary_kpi", "result": {"revenue": 10}}]
    latest_results = [{"tool": "get_top_products", "result": {"count": 5}}]
    conversation.add_message(Message(role="assistant", content="First", tool_results=first_results))
    conversation.add_message(Message(role="user", content="Only in Asia."))
    conversation.add_message(Message(role="assistant", content="Latest", tool_results=latest_results))

    assert conversation.last_tool_results() == latest_results


def test_last_tool_results_is_empty_when_no_assistant_tool_call_exists():
    conversation = Conversation(id="conversation-1")
    conversation.add_message(Message(role="user", content="Hello"))
    conversation.add_message(Message(role="assistant", content="Hello."))

    assert conversation.last_tool_results() == []