"""LangChain agent - SQL sub-graph (LangGraph).

Explicit state graph for the dynamic-SQL path: discover_schema ->
generate_sql -> validate_sql -> execute_sql, with a bounded retry back to
generate_sql on a validation or execution failure. Replaces the P0-era
design where the outer tool-calling agent authored SQL directly as a
tool argument and retried by calling the tool again (bounded by a
per-turn attempt counter in tools/sql_tools.py) - that outer-level
counter is now redundant and removed: this graph bounds its own retries
internally and always resolves (success or a clean final failure) within
one outer tool call, with the actual error fed back into the next
generation attempt rather than a blunt "try again" signal.

Modeling each stage as its own graph node (rather than folding it into
one tool function) is what makes each stage independently unit-testable
with a fake state/fake LLM, and makes the retry bound's termination
directly testable by walking a scripted state through the graph.
"""

from typing import Optional, TypedDict

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage
from langgraph.graph import END, StateGraph

from config.settings import SQL_AGENT_MAX_RETRIES
from database.connection.connection_pool import serialize_row
from langchain_app.llm import get_llm
from langchain_app.sql_context import build_sql_generation_context
from langchain_app.sql_db import get_execution_sql_database
from langchain_app.sql_validation import validate_select_only

_GENERATE_SQL_PROMPT = """Write a single read-only PostgreSQL SELECT statement \
that answers the question below, using only the schema context provided. \
Return ONLY the SQL statement - no explanation, no markdown code fences.

When a selected column is a foreign key referencing a dimension table \
(e.g. `region_id` -> `regions`, `product_id` -> `products`, `customer_id` \
-> `customers`), JOIN to that table and select its human-readable name \
column (e.g. `region_name`, `product_name`, `customer_name`) instead of \
the raw id - unless the question explicitly asks for the id itself. A \
plain listing of an entity's own table (e.g. "list all customers") still \
needs the id-referencing dimension resolved, not left as a bare number.

Question: {question}

Schema context:
{schema_context}
{retry_note}"""


class SQLGraphState(TypedDict):
    question: str
    schema_context: str
    generated_sql: str
    error: Optional[str]
    rows: Optional[list[dict]]
    attempt: int


def _strip_code_fence(text: str) -> str:
    """Strip a markdown code fence around generated SQL, if the model
    added one despite the prompt asking it not to."""
    text = text.strip()
    if text.startswith("```"):
        lines = text.splitlines()[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        text = "\n".join(lines).strip()
    return text


def discover_schema(state: SQLGraphState) -> dict:
    """Structural reflection + retrieved business context for this question."""
    return {"schema_context": build_sql_generation_context(state["question"])}


def generate_sql(state: SQLGraphState, llm: Optional[BaseChatModel] = None) -> dict:
    """Ask the LLM for a SQL statement given the question and schema
    context. On a retry, the previous attempt's error is fed back into
    the prompt so the model can correct it, instead of guessing blind."""
    llm = llm or get_llm()
    retry_note = f"\nThe previous attempt failed: {state['error']}\nFix it." if state.get("error") else ""
    prompt = _GENERATE_SQL_PROMPT.format(
        question=state["question"], schema_context=state["schema_context"], retry_note=retry_note
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return {
        "generated_sql": _strip_code_fence(response.content or ""),
        "attempt": state.get("attempt", 0) + 1,
        "error": None,
    }


def validate_sql(state: SQLGraphState) -> dict:
    """Deterministic safety gate (sql_validation.py) - a rejection here
    feeds back into the next generate_sql attempt, it never raises."""
    try:
        checked = validate_select_only(state["generated_sql"])
    except Exception as exc:  # noqa: BLE001 - fed back into the next generation attempt
        return {"error": str(exc)}
    return {"generated_sql": checked, "error": None}


def execute_sql(state: SQLGraphState) -> dict:
    """Run the validated query through the restricted read-only role. A
    DB error (e.g. an unknown column the validator can't catch) feeds
    back into the next generate_sql attempt the same way a validation
    failure does.

    Rows are normalized through the same `serialize_row()` the fixed
    business tools' DAOs use (database.connection.connection_pool) - a raw
    SUM()/AVG() aggregate comes back as `decimal.Decimal`, which
    `chart_data.extract_chart_data()`'s numeric check doesn't recognize,
    so an un-normalized Decimal column silently made every answer_with_sql
    result look non-chart-worthy (the "Show chart" button never appearing
    when FIXED_TOOLS_ENABLED=false, since answer_with_sql is the only
    data-returning tool in that configuration).
    """
    try:
        result = get_execution_sql_database().run(state["generated_sql"], fetch="cursor")
        rows = [serialize_row(row._mapping) for row in result]
    except Exception as exc:  # noqa: BLE001 - fed back into the next generation attempt
        return {"error": str(exc)}
    return {"rows": rows, "error": None}


def _after_validate(state: SQLGraphState) -> str:
    if state.get("error"):
        return "retry" if state["attempt"] < SQL_AGENT_MAX_RETRIES else "give_up"
    return "execute"


def _after_execute(state: SQLGraphState) -> str:
    if state.get("error"):
        return "retry" if state["attempt"] < SQL_AGENT_MAX_RETRIES else "give_up"
    return "done"


def build_sql_graph(llm: Optional[BaseChatModel] = None):
    """Construct the compiled graph. `llm` is overridable (DI) so this
    can be exercised in tests with a scripted fake chat model."""
    graph = StateGraph(SQLGraphState)
    graph.add_node("discover_schema", discover_schema)
    graph.add_node("generate_sql", lambda state: generate_sql(state, llm=llm))
    graph.add_node("validate_sql", validate_sql)
    graph.add_node("execute_sql", execute_sql)

    graph.set_entry_point("discover_schema")
    graph.add_edge("discover_schema", "generate_sql")
    graph.add_edge("generate_sql", "validate_sql")
    graph.add_conditional_edges(
        "validate_sql", _after_validate, {"execute": "execute_sql", "retry": "generate_sql", "give_up": END}
    )
    graph.add_conditional_edges(
        "execute_sql", _after_execute, {"done": END, "retry": "generate_sql", "give_up": END}
    )
    return graph.compile()


def run_sql_graph(question: str, llm: Optional[BaseChatModel] = None) -> SQLGraphState:
    """Run the SQL sub-graph for one question end to end, returning the
    final state - `rows` populated on success, `error` set on a final
    (retry-exhausted) failure."""
    app = build_sql_graph(llm=llm)
    initial_state: SQLGraphState = {
        "question": question,
        "schema_context": "",
        "generated_sql": "",
        "error": None,
        "rows": None,
        "attempt": 0,
    }
    return app.invoke(initial_state)
