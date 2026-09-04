"""Domain Model - Conversation.

Represents a multi-turn conversation session
(docs/business_description.md > Workshop Goals: Conversation Memory Management).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from langchain_core.messages import AIMessage, BaseMessage, HumanMessage

from backend.models.message import Message


@dataclass
class Conversation:
    id: str
    messages: list[Message] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, message: Message) -> None:
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)

    def chat_history(self) -> list[BaseMessage]:
        """Prior turns as LangChain messages, for `langchain_app.agent.run_turn()`'s `chat_history`.

        Only plain text round-trips here - each turn's tool-calling
        reasoning lives in that turn's own `agent_scratchpad` and is not
        replayed on later turns (the agent still sees its own tool results
        summarized into the assistant's final answer text).
        """
        history: list[BaseMessage] = []
        for msg in self.messages:
            if msg.role == "user":
                history.append(HumanMessage(content=msg.content))
            else:
                history.append(AIMessage(content=msg.content))
        return history

    def last_tool_results(self) -> list[dict[str, Any]]:
        """Tool results from the most recent assistant turn that made any.

        Used by insight/recommendation generation so they can reuse
        already-retrieved data instead of invoking a tool (and hitting the
        database) again.
        """
        for msg in reversed(self.messages):
            if msg.role == "assistant" and msg.tool_results:
                return msg.tool_results
        return []
