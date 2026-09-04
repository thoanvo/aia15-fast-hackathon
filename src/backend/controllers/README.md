# backend/controllers/

`chat_controller.py` — `APIRouter(prefix="/chat")`, mounted under
`/api/v1` by `src/app.py`.

| Route | Purpose |
|---|---|
| `POST /chat` | One chat turn; body `{conversation_id, question}` → `{conversation_id, answer, source_tables}`. |
| `GET /chat/{id}/history` | Full message history for a conversation. |
| `POST /chat/{id}/insight` | Business insight from the conversation's most recently retrieved tool result. |
| `POST /chat/{id}/recommendation` | Actionable recommendations from previously generated insight text. |
| `DELETE /chat/{id}` | Clear a conversation's history. |

Service-layer exceptions are caught and logged, returning a clean `500`
rather than leaking internals; Pydantic request validation (e.g. a
missing `question`) returns FastAPI's standard `422`.
