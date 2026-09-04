"""Domain Model - Message.

One turn in a Conversation. Simpler than a raw OpenAI tool-calling message
(no `tool_calls`/`tool_call_id`) because `langchain_app.agent`'s
`AgentExecutor` owns the entire tool-calling loop and its scratchpad
within a single turn - only the plain user/assistant text needs to persist
across turns as `chat_history`. `tool_results` keeps the raw tool outputs
from an assistant turn so insight/recommendation generation
(`insight_service`/`recommendation_service`) can reuse them without
re-invoking a tool (and hitting the database again).
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Literal, Optional

Role = Literal["user", "assistant"]


@dataclass
class Message:
    role: Role
    content: str
    # DB tables the tool calls behind this answer read from (see
    # langchain_app.table_sources) - only meaningful on assistant turns,
    # for UI "data source" attribution.
    source_tables: list[str] = field(default_factory=list)
    # Raw {"tool": ..., "args": ..., "result": ...} entries from this turn's
    # AgentExecutor.intermediate_steps - only meaningful on assistant turns.
    tool_results: list[dict[str, Any]] = field(default_factory=list)
    # Knowledge-base chunks retrieved by search_knowledge_base during this turn,
    # for UI attribution of which KB entries backed the answer.
    kb_chunks: list[str] = field(default_factory=list)
    # Chart-ready [{"x": ..., "y": ...}, ...] records from this turn's most
    # recent tool result (langchain_app.chart_data.extract_chart_data()), or
    # None when nothing chart-worthy was found - only meaningful on
    # assistant turns.
    chart_data: Optional[list[dict[str, Any]]] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
