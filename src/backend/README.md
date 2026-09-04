# backend/

Thin service/controller layer sitting on top of `langchain_app/` (the AI
core) and `database/` (persistence, indirectly via the agent's tools).
One endpoint family: `POST /api/v1/chat` + insight/recommendation/history/
clear.

- `controllers/chat_controller.py` — `POST /chat`, `GET /chat/{id}/history`, `POST /chat/{id}/insight`, `POST /chat/{id}/recommendation`, `DELETE /chat/{id}`
- `models/{conversation,message}.py` — in-memory conversation state
- `services/chat_service.py` — conversation store + per-conversation locking, delegates each turn to `langchain_app.agent.run_turn()`
- `services/insight_service.py` / `recommendation_service.py` — reuse `langchain_app.llm.get_llm()` directly against the conversation's last tool result(s), bypassing the agent's tool-calling loop

**Status:** Phase 5 complete. There is no hand-rolled multi-round
tool-calling loop here — `langchain_app.agent`'s `AgentExecutor` already
owns that; `chat_service` only owns conversation storage/locking and
converts stored turns to/from LangChain `chat_history`. Verified
end-to-end with `TestClient` against `backend.services.chat_service`'s
`_agent_executor` swapped for one built with a scripted fake chat model
(no real OpenAI-compatible endpoint needed) — health checks, a full chat
turn, a follow-up turn reusing `chat_history`, the "no data yet" insight
guard message, insight/recommendation reuse of the last tool result,
request validation, and conversation clearing all pass. See
`services/README.md` for the insight/recommendation stubbing pattern.
