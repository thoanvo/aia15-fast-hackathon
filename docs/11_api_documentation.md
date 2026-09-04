# API Documentation

`src/app.py` — FastAPI composition root. All routes below are prefixed
with `/api/v1` except the two health checks. Interactive docs (Swagger UI)
are available at `/docs` once the backend is running (see
[`09_environment_setup_guide.md`](09_environment_setup_guide.md)).

## Health

### `GET /health`

Basic liveness check — does the backend process respond at all.

**Response `200`**
```json
{"status": "ok"}
```

### `GET /health/db`

Verifies the configured PostgreSQL (Neon) connection is reachable.

**Response `200`**
```json
{"status": "ok"}
```

**Response `503`** (database unreachable)
```json
{"detail": "Database unreachable: <error>"}
```

## Chat

### `POST /api/v1/chat`

One chat turn: sends a question to the LangChain agent (business tools +
RAG retrieval, see [`05_system_architecture.md`](05_system_architecture.md))
and returns the answer plus which DB table(s) it was sourced from.

**Request**
```json
{"conversation_id": "any-client-chosen-string", "question": "What are the top 5 products by revenue?"}
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `conversation_id` | string | yes | Client-chosen id for the conversation session; reused across turns for context. |
| `question` | string | yes | The user's natural-language question (English or Vietnamese). |

**Response `200`**
```json
{
  "conversation_id": "any-client-chosen-string",
  "answer": "The top 5 products by revenue are ...",
  "source_tables": ["sales", "products", "regions"]
}
```

`source_tables` is empty when the answer didn't require a business-data
tool call (e.g. an out-of-scope refusal, or a knowledge-base-only answer
via the retrieval tool).

**Response `422`** — Pydantic validation error (e.g. missing `question`).
**Response `500`** — unexpected failure; the detail message never leaks
internals (see the error is logged server-side instead).

### `GET /api/v1/chat/{conversation_id}/history`

Full message history for a conversation, in order.

**Response `200`**
```json
{
  "conversation_id": "any-client-chosen-string",
  "messages": [
    {"role": "user", "content": "What are the top 5 products by revenue?", "source_tables": []},
    {"role": "assistant", "content": "The top 5 products ...", "source_tables": ["sales", "products", "regions"]}
  ]
}
```

An unknown `conversation_id` returns an empty `messages` list (a
conversation is created implicitly on first use, not on lookup).

### `POST /api/v1/chat/{conversation_id}/insight`

Generates a business insight from the conversation's most recently
retrieved tool result (does not call a tool again or touch the database
directly — see `backend/services/insight_service.py`).

**Request**
```json
{"question": "What insights can you provide?"}
```

**Response `200`**
```json
{"conversation_id": "any-client-chosen-string", "insight": "**Key Insights:**\n- ..."}
```

If no data has been retrieved yet in this conversation, `insight` is a
guard message asking the user to ask a data question first (not an error
— still `200`).

### `POST /api/v1/chat/{conversation_id}/recommendation`

Turns previously generated insight text into actionable recommendations.

**Request**
```json
{"insight": "**Key Insights:**\n- Asia leads in laptop revenue."}
```

**Response `200`**
```json
{"conversation_id": "any-client-chosen-string", "recommendation": "**Recommendations:**\n1. ..."}
```

### `DELETE /api/v1/chat/{conversation_id}`

Clears a conversation's history (e.g. a "Clear chat" UI action).

**Response `200`**
```json
{"conversation_id": "any-client-chosen-string", "status": "cleared"}
```

## Error shape

All non-2xx responses use FastAPI's standard error body:
```json
{"detail": "<message>"}
```
