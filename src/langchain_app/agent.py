"""LangChain agent - AgentExecutor construction.

Single unified tool-calling agent (business tools + retrieval tool) over
one prompt - see the plan doc's "One agent, one endpoint" architecture
decision: a single turn can freely mix live business-data lookups and
schema/SQL knowledge-base questions, instead of splitting retrieval and
function-calling into two separate chains/endpoints.
"""

import logging
import re
from collections import Counter
from typing import Any, Optional

from langchain_classic.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import BaseMessage
from langchain_core.tools import BaseTool

from config.settings import (
    AGENT_MAX_EXECUTION_TIME_SECONDS,
    AGENT_MAX_ITERATIONS,
    OOS_ENABLED,
    is_fixed_tools_enabled,
)
from langchain_app.chart_data import extract_chart_data
from langchain_app.llm import get_llm
from langchain_app.oos_guard import check_scope

# tools.business_tools/retrieval_tool/sql_tools must import before
# prompts/table_sources: importing this package's __init__.py forces the
# embedding model (torch) to load first, before any sibling import can
# pull in SQLAlchemy (business_tools -> database.dao, or sql_tools ->
# sql_graph -> sql_db) - same Windows DLL load-order guard as
# tools/__init__.py.
from langchain_app.tools.business_tools import get_business_tools
from langchain_app.tools.retrieval_tool import get_retrieval_tool
from langchain_app.tools.sql_tools import get_sql_tools

from langchain_app.prompts import get_agent_prompt
from langchain_app.table_sources import get_source_tables_for_steps

logger = logging.getLogger(__name__)

# Only the two patterns the user explicitly requested; prose is never touched.
_NUMBERED_BOLD_HEADING = re.compile(r"^(\s*\d+\.\s+)\*\*([^*]+?)\*\*\s*$")
_KV_BULLET = re.compile(r"^(\s*[-*+]\s+)((?:[^:\n]+):\s+\S[^\n]*)(\s*)$")

# Tool-name -> routing-mode classification, for trace logging (which mode -
# FIXED_TOOL vs DYNAMIC_SQL - actually got called each turn, per
# plan/HACK-B03_Fixed_Tool_Feature_Flag.md's routing-verification ask).
# Derived from the tool objects themselves rather than hardcoded name
# strings, so a rename of sql_db_schema/answer_with_sql/search_knowledge_base
# can't silently desync this classification from get_tools().
_DYNAMIC_SQL_TOOL_NAMES = {t.name for t in get_sql_tools()}
_RETRIEVAL_TOOL_NAME = get_retrieval_tool().name


def _tool_mode(tool_name: str) -> str:
    if tool_name in _DYNAMIC_SQL_TOOL_NAMES:
        return "DYNAMIC_SQL"
    if tool_name == _RETRIEVAL_TOOL_NAME:
        return "RETRIEVAL"
    return "FIXED_TOOL"


def normalize_assistant_answer(answer: str) -> str:
    lines: list[str] = []
    in_code_block = False

    for line in answer.splitlines():
        stripped = line.strip()
        if stripped.startswith("```"):
            in_code_block = not in_code_block
            lines.append(line)
            continue
        if in_code_block or not stripped:
            lines.append(line)
            continue

        heading = _NUMBERED_BOLD_HEADING.match(line)
        if heading:
            prefix, name = heading.group(1), heading.group(2).rstrip(" .:!?;")
            lines.append(f"{prefix}**{name}:**")
            continue

        bullet = _KV_BULLET.match(line)
        if bullet:
            prefix, content, trailing = bullet.groups()
            if content[-1] not in ".!?:;":
                content = f"{content}."
            lines.append(f"{prefix}{content}{trailing}")
            continue

        lines.append(line)

    return "\n".join(lines)


def get_tools(fixed_tools_enabled: Optional[bool] = None) -> list[BaseTool]:
    """All tools available to the agent: the retrieval tool and the
    dynamic-SQL tools are always registered, plus the fixed business
    tools when fixed_tools_enabled (defaults to the current
    config.settings.is_fixed_tools_enabled() state, read fresh so a
    runtime toggle is picked up on the next call)."""
    if fixed_tools_enabled is None:
        fixed_tools_enabled = is_fixed_tools_enabled()
    business_tools = get_business_tools() if fixed_tools_enabled else []
    tools = [*business_tools, get_retrieval_tool(), *get_sql_tools()]
    logger.info(
        "Tool registration | FIXED_TOOLS_ENABLED=%s fixed_tools=%d dynamic_sql_tools=%d "
        "retrieval_tools=1 total=%d names=%s",
        fixed_tools_enabled,
        len(business_tools),
        len(_DYNAMIC_SQL_TOOL_NAMES),
        len(tools),
        [t.name for t in tools],
    )
    return tools


def build_agent_executor(
    llm: Optional[BaseChatModel] = None, tools: Optional[list[BaseTool]] = None
) -> AgentExecutor:
    """Construct the AgentExecutor.

    `llm`/`tools` are overridable (dependency injection) so this can be
    exercised in tests with a scripted fake chat model instead of a real
    OpenAI-compatible endpoint. Reads is_fixed_tools_enabled() once so the
    tool list and the prompt it's paired with agree on the same value even
    if the runtime toggle flips mid-call.
    """
    llm = llm or get_llm()
    fixed_tools_enabled = is_fixed_tools_enabled()
    tools = tools if tools is not None else get_tools(fixed_tools_enabled)
    agent = create_tool_calling_agent(llm, tools, get_agent_prompt(fixed_tools_enabled))
    return AgentExecutor(
        agent=agent,
        tools=tools,
        return_intermediate_steps=True,
        max_iterations=AGENT_MAX_ITERATIONS,
        max_execution_time=AGENT_MAX_EXECUTION_TIME_SECONDS,
    )


def run_turn(
    agent_executor: AgentExecutor,
    question: str,
    chat_history: Optional[list[BaseMessage]] = None,
    oos_llm: Optional[BaseChatModel] = None,
) -> dict[str, Any]:
    """Run one agent turn.

    Out-of-scope detection (`oos_guard.check_scope()`) runs first, per
    docs/03_functional_and_out_of_scope_requirements.md - a rejected
    question never reaches the agent at all (no tool call, no retrieval,
    no agent-loop LLM call). Set `OOS_ENABLED=false` to disable this and
    fall back to the agent's own system-prompt scope rules only.

    Returns `{"answer": str, "source_tables": list[str], "tool_results": list[dict],
    "kb_chunks": list[str], "chart_data": list[dict] | None}` -
    `backend.services.chat_service` is the intended caller, which owns
    converting its own conversation state into `chat_history` (a list of
    LangChain `BaseMessage`s) and persisting the result. `tool_results` is
    the raw `{"tool", "args", "result"}` per call this turn, for
    `insight_service`/`recommendation_service` to reuse without invoking a
    tool (and hitting the database) again. `source_tables` is always
    empty for a rejected question - it never touched the database.
    `kb_chunks` contains the raw text blocks returned by `search_knowledge_base`
    during this turn, for UI display of which knowledge base entries were used.
    `chart_data` is a deterministic, no-LLM-call heuristic
    (`chart_data.extract_chart_data()`) over this turn's tool results -
    `None` when nothing chart-worthy was found (the common case), not an
    error.
    """
    if OOS_ENABLED:
        try:
            oos_result = check_scope(question, llm=oos_llm, chat_history=chat_history)
        except Exception:  # noqa: BLE001 - a broken classifier/embedding call must not block an otherwise-fine turn
            logger.exception("OOS check failed; failing open and proceeding to the agent for this turn")
        else:
            if not oos_result.in_scope:
                logger.info("Turn routing | question=%r mode=REJECTED_OOS tool_calls=0", question)
                return {
                    "answer": oos_result.message,
                    "source_tables": [],
                    "tool_results": [],
                    "kb_chunks": [],
                    "chart_data": None,
                }

    result = agent_executor.invoke({"input": question, "chat_history": chat_history or []})
    intermediate_steps = result.get("intermediate_steps", [])
    for step_index, (action, observation) in enumerate(intermediate_steps, start=1):
        logger.info(
            "Tool call %d/%d | mode=%s tool=%s args=%s",
            step_index,
            len(intermediate_steps),
            _tool_mode(action.tool),
            action.tool,
            action.tool_input,
        )
    mode_counts = Counter(_tool_mode(action.tool) for action, _ in intermediate_steps)
    logger.info(
        "Turn routing | question=%r tool_calls=%d modes=%s",
        question,
        len(intermediate_steps),
        dict(mode_counts),
    )
    source_tables = get_source_tables_for_steps(intermediate_steps)
    tool_results = [
        {"tool": action.tool, "args": action.tool_input, "result": observation}
        for action, observation in intermediate_steps
    ]
    # Collect KB chunks from every search_knowledge_base call this turn.
    # Each observation is a single string of "\n\n---\n\n"-separated chunks
    # (see retrieval_tool.py). Split so the UI can render them individually.
    kb_chunks: list[str] = []
    for action, observation in intermediate_steps:
        if action.tool == "search_knowledge_base" and isinstance(observation, str):
            kb_chunks.extend(
                chunk.strip() for chunk in observation.split("\n\n---\n\n") if chunk.strip()
            )
    return {
        "answer": normalize_assistant_answer(result["output"]),
        "source_tables": source_tables,
        "tool_results": tool_results,
        "kb_chunks": kb_chunks,
        "chart_data": extract_chart_data(tool_results),
    }
