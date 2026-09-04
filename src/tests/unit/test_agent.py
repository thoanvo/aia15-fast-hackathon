from types import SimpleNamespace

from langchain_app import agent
from tests.unit.helpers import FakeExecutor


def test_get_tools_excludes_business_tools_when_flag_disabled(monkeypatch):
    monkeypatch.setattr(agent, "is_fixed_tools_enabled", lambda: False)

    names = [tool.name for tool in agent.get_tools()]

    assert "get_top_products" not in names
    assert names.count("search_knowledge_base") == 1
    assert "sql_db_schema" in names
    assert "answer_with_sql" in names
    assert len(names) == 3


def test_get_tools_includes_business_tools_when_flag_enabled(monkeypatch):
    monkeypatch.setattr(agent, "is_fixed_tools_enabled", lambda: True)

    names = [tool.name for tool in agent.get_tools()]

    assert names.count("get_top_products") == 1
    assert names.count("search_knowledge_base") == 1
    assert "sql_db_schema" in names
    assert "answer_with_sql" in names
    assert len(names) == 19


def test_get_tools_respects_explicit_argument_over_the_current_flag(monkeypatch):
    """An explicit fixed_tools_enabled argument overrides the ambient
    setting - build_agent_executor() relies on this to keep the tool list
    and the prompt it's paired with consistent within one call, even if
    the runtime toggle flips mid-call."""
    monkeypatch.setattr(agent, "is_fixed_tools_enabled", lambda: True)

    names = [tool.name for tool in agent.get_tools(fixed_tools_enabled=False)]

    assert "get_top_products" not in names
    assert len(names) == 3


def test_get_tools_matches_real_environment_flag_state():
    """Whatever FIXED_TOOLS_ENABLED actually resolves to from the real .env
    in this environment (not mocked) - 19 tools when on, 3 when off -
    get_tools() must match it. Deliberately doesn't assert a specific
    value: FIXED_TOOLS_ENABLED is meant to be environment-configurable, so
    a real .env change (e.g. a developer turning it off to test the
    dynamic-SQL-only path locally) must not make this test start failing."""
    expected_count = 19 if agent.is_fixed_tools_enabled() else 3
    assert len(agent.get_tools()) == expected_count


def test_run_turn_forwards_history_and_extracts_tool_results(monkeypatch):
    steps = [
        (SimpleNamespace(tool="get_top_products", tool_input={"limit": 5}), {"count": 5}),
    ]
    executor = FakeExecutor({"output": "Top products", "intermediate_steps": steps})
    monkeypatch.setattr(agent, "OOS_ENABLED", False)

    result = agent.run_turn(executor, "Show products", chat_history=["previous"])

    assert executor.calls == [{"input": "Show products", "chat_history": ["previous"]}]
    assert result == {
        "answer": "Top products",
        "source_tables": ["sales", "products", "regions"],
        "tool_results": [
            {"tool": "get_top_products", "args": {"limit": 5}, "result": {"count": 5}},
        ],
        "kb_chunks": [],
        "chart_data": None,
    }


def test_run_turn_rejects_out_of_scope_without_invoking_executor(monkeypatch):
    executor = FakeExecutor({"output": "should not run"})
    monkeypatch.setattr(agent, "OOS_ENABLED", True)
    monkeypatch.setattr(
        agent,
        "check_scope",
        lambda question, llm=None, chat_history=None: SimpleNamespace(in_scope=False, message="Rejected"),
    )

    result = agent.run_turn(executor, "Tell me a joke")

    assert result == {
        "answer": "Rejected",
        "source_tables": [],
        "tool_results": [],
        "kb_chunks": [],
        "chart_data": None,
    }
    assert executor.calls == []


def test_run_turn_fails_open_when_oos_check_raises(monkeypatch):
    executor = FakeExecutor({"output": "Business answer", "intermediate_steps": []})
    monkeypatch.setattr(agent, "OOS_ENABLED", True)

    def fail_scope(question, llm=None, chat_history=None):
        raise RuntimeError("classifier timeout")

    monkeypatch.setattr(agent, "check_scope", fail_scope)

    result = agent.run_turn(executor, "Show revenue")

    assert result["answer"] == "Business answer"
    assert len(executor.calls) == 1
