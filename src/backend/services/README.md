# backend/services/

- `chat_service.py` — in-memory conversation store keyed by `conversation_id`, one `threading.Lock` per conversation (FastAPI runs sync endpoints in a threadpool, so concurrent requests for the same conversation could otherwise race on its message list). `handle_message()` reads `conversation.chat_history()` (prior turns only), calls `langchain_app.agent.run_turn()`, then persists both the user turn and the assistant's answer/`source_tables`/`tool_results`. The `AgentExecutor` is built lazily on first use (`_get_agent_executor()`), not at import time, so importing this module never requires real `OPENAI_*` credentials.
- `insight_service.py` — `generate_business_insight()`: if the conversation has no `last_tool_results()` yet, returns a guard message (`NO_DATA_MESSAGE`) instead of calling the LLM. Otherwise formats `langchain_app.prompts.INSIGHT_PROMPT` with the most recent tool result and calls `langchain_app.llm.get_llm()` directly — no agent/tool loop.
- `recommendation_service.py` — `generate_recommendation()`: formats `langchain_app.prompts.RECOMMENDATION_PROMPT` with previously generated insight text and calls `get_llm()` directly.

## Testing without a real LLM

Both `insight_service`/`recommendation_service` call `get_llm()` as a
plain module-level function reference, so a test can monkeypatch
`insight_service.get_llm` / `recommendation_service.get_llm` to a lambda
returning a scripted fake chat model — no real API key needed. Similarly,
`chat_service._agent_executor` can be swapped for one built via
`langchain_app.agent.build_agent_executor(llm=<fake>, tools=<real tools>)`
to exercise the full HTTP → controller → service → agent path against a
scripted chat model instead of a real gateway.
