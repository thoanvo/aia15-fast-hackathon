"""Service Layer - Chat Service.

Responsibilities (docs/business_description.md > Technical Architecture >
Service Layer): orchestrate one chat turn, handle multi-turn conversations,
manage conversation memory. Unlike an OpenAI-native hand-rolled
tool-calling loop, there is no per-round bookkeeping here -
`langchain_app.agent`'s `AgentExecutor` already owns that; this module
only owns conversation state (storage + locking) and delegates each turn
to it.
"""

import threading
from typing import Any, Optional

from langchain_classic.agents import AgentExecutor

from langchain_app.agent import build_agent_executor, run_turn
from backend.models.conversation import Conversation
from backend.models.message import Message
from config.settings import is_fixed_tools_enabled

# In-memory conversation store keyed by conversation_id - sufficient for
# this workshop's scope (single-process, no persistence across restarts).
_conversations: dict[str, Conversation] = {}

# Per-conversation locks. FastAPI runs sync endpoints in a threadpool, so
# concurrent requests for the same conversation_id could otherwise race on
# the same message list. Serialize per conversation_id to prevent that.
_locks_guard = threading.Lock()
_conversation_locks: dict[str, threading.Lock] = {}

# Built lazily on first use (not at import time) so importing this module
# never requires real OPENAI_* credentials - only actually handling a
# message does.
_agent_executor: Optional[AgentExecutor] = None
# The FIXED_TOOLS_ENABLED state _agent_executor was built with - compared
# against the current value on every call so the frontend's runtime toggle
# (backend.controllers.settings_controller) triggers a rebuild with the
# right tools/prompt instead of serving the stale cached executor for the
# rest of the process's life.
_agent_executor_fixed_tools_enabled: Optional[bool] = None


def _get_agent_executor() -> AgentExecutor:
    global _agent_executor, _agent_executor_fixed_tools_enabled
    current = is_fixed_tools_enabled()
    if _agent_executor is None or _agent_executor_fixed_tools_enabled != current:
        _agent_executor = build_agent_executor()
        _agent_executor_fixed_tools_enabled = current
    return _agent_executor


def lock_for(conversation_id: str) -> threading.Lock:
    """Return the lock serializing access to one conversation_id's history."""
    with _locks_guard:
        lock = _conversation_locks.get(conversation_id)
        if lock is None:
            lock = threading.Lock()
            _conversation_locks[conversation_id] = lock
        return lock


def get_conversation(conversation_id: str) -> Conversation:
    """Return the Conversation for this id, creating an empty one if new."""
    conversation = _conversations.get(conversation_id)
    if conversation is None:
        conversation = Conversation(id=conversation_id)
        _conversations[conversation_id] = conversation
    return conversation


def reset_conversation(conversation_id: str) -> None:
    """Drop a conversation's history (e.g. on a "clear chat" action)."""
    _conversations.pop(conversation_id, None)


def handle_message(conversation_id: str, question: str) -> dict[str, Any]:
    """Handle one user turn end to end.

    Follow-up questions (e.g. "Only in Asia." after "top products by
    revenue") are resolved naturally: the prior turns are sent to the
    agent as `chat_history` on every call, so it has the context to
    reinterpret a short follow-up without any special-casing here.

    Returns `{"answer": str, "source_tables": list[str], "kb_chunks": list[str],
    "chart_data": list[dict] | None}`.
    """
    with lock_for(conversation_id):
        conversation = get_conversation(conversation_id)
        history = conversation.chat_history()  # prior turns only, not this one

        result = run_turn(_get_agent_executor(), question, chat_history=history)

        conversation.add_message(Message(role="user", content=question))
        conversation.add_message(
            Message(
                role="assistant",
                content=result["answer"],
                source_tables=result["source_tables"],
                tool_results=result["tool_results"],
                kb_chunks=result.get("kb_chunks", []),
                chart_data=result.get("chart_data"),
            )
        )
        return {
            "answer": result["answer"],
            "source_tables": result["source_tables"],
            "kb_chunks": result.get("kb_chunks", []),
            "chart_data": result.get("chart_data"),
        }
