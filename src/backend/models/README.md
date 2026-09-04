# backend/models/

In-memory domain models for conversation state.

- `message.py` — `Message`: one turn (`role`, `content`, `source_tables`, `tool_results`). Simpler than a raw OpenAI tool-calling message (no `tool_calls`/`tool_call_id`) since `langchain_app.agent`'s `AgentExecutor` owns the tool-calling loop entirely within a single turn.
- `conversation.py` — `Conversation`: ordered `Message` list + `chat_history()` (converts stored turns to LangChain `HumanMessage`/`AIMessage` for `langchain_app.agent.run_turn()`) + `last_tool_results()` (for `insight_service`/`recommendation_service` to reuse without re-invoking a tool).
