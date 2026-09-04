# Backend High-Level Architecture

Source: `src/langchain_app/`, `src/backend/`, `src/database/` — see each
folder's `README.md` and `01_business_requirements.md` (Technical
Architecture) for details. See
[`04_solution_design.md`](04_solution_design.md)
for the full rationale behind these choices, and
[`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md)
for the full detail behind the dynamic-SQL and embedding/RAG pieces this
document now includes — this document stays at the layered-overview
level; `12` is the source of truth for `sql_context.py`/`sql_graph.py`/
`sql_db.py`/`sql_validation.py`/`tools/sql_tools.py` internals.

## Layered view

```
                         +----------------------+
                         |  Client (curl / UI)  |
                         +----------------------+
                                    |
                                    | HTTP POST /api/v1/chat
                                    v
        +----------------------------------------------------------+
        |               BACKEND LAYER (src/backend)                 |
        |                                                            |
        |  app.py -> controllers/ -> services/ -> models/             |
        |             (chat_controller)  (chat_service,               |
        |                                  insight_service,           |
        |                                  recommendation_service)    |
        +---------------------------------|--------------------------+
                                           | delegates to
                                           v
        +----------------------------------------------------------+
        |          LANGCHAIN APP LAYER (src/langchain_app)           |
        |                                                            |
        |  oos_guard.py -- check_scope() gate, runs before the agent  |
        |    (Layer 0-2: prompt-injection screen, LLM intent          |
        |    classifier, FAISS-similarity threshold - rejects here    |
        |    never reach the agent/tools/DB at all)                   |
        |         |                                                    |
        |         v                                                    |
        |  agent.py                                                  |
        |    create_tool_calling_agent(llm, tools, prompt)            |
        |    -> AgentExecutor.invoke() -> intermediate_steps          |
        |         |                              |                    |
        |         v                              v                    |
        |  prompts.py                     table_sources.py            |
        |   (ChatPromptTemplate:           (tool name -> table(s),    |
        |    scope rules, refusal,          UI attribution)           |
        |    few-shot examples)                                       |
        |         |                                                    |
        |         v                                                    |
        |  llm.py -> ChatOpenAI (gateway base_url/http_client,         |
        |             per-call random seed override)                  |
        |                                                              |
        |  tools/ (get_tools() = all of the below)                     |
        |   business_tools.py -- StructuredTool x16, wraps DAO calls   |
        |                         (gated by FIXED_TOOLS_ENABLED)       |
        |   retrieval_tool.py -- @tool wrapping FAISS retriever        |
        |   sql_tools.py      -- answer_with_sql / sql_db_schema       |
        |                         (always registered)                 |
        |         |                    |                    |          |
        |         v                    |                    v          |
        |  (calls database.dao)        |         sql_graph.py (LangGraph state machine)
        |                               |           discover_schema -> generate_sql ->
        |                               |           validate_sql -> execute_sql
        |                               |           (bounded retry on validate/execute failure)
        |                               |             |            |            |
        |                               |             v            v            v
        |                               |      sql_context.py  sql_validation.py  sql_db.py
        |                               |      (structural       (SELECT-only,   (2 engines:
        |                               |       floor + FAISS     single-stmt,    reflection on
        |                               |       retrieval)        LIMIT cap)      main engine,
        |                               |             |                          execution on
        |                               v             v                          readonly_pool)
        |                        vectorstore/  <-------------------------------------+
        |                         embeddings.py (HuggingFaceEmbeddings, shared model)  |
        |                         store.py (ONE FAISS index over embedding/ docs -    |
        |                          two consumers: retrieval_tool.py's k=3 and         |
        |                          sql_context.py's k=SQL_CONTEXT_RETRIEVAL_K)        |
        +----------------|---------------------------------------------|--------------+
                          v                                             v
        +----------------------------------+   +----------------------------------------+
        |  DATABASE LAYER (src/database)     |   | readonly_pool.py's restricted role     |
        |                                     |   | (falls back to DATABASE_URL if unset,  |
        |  dao/ -> connection/connection_pool.py |  local-dev only) - execution path for  |
        |        -> PostgreSQL / Neon         |   | model-generated SQL only                |
        +-------------------------------------+   +----------------------------------------+
```

## Request/response flow (one chat turn)

1. **Backend layer** — `app.py` mounts `chat_controller`; the controller
   validates the HTTP request and calls `chat_service.handle_message()`.
2. **Out-of-scope gate** — `agent.run_turn()` calls `oos_guard.check_scope()`
   first, per [`03_functional_and_out_of_scope_requirements.md`](03_functional_and_out_of_scope_requirements.md).
   A rejected question returns a friendly decline immediately — no tool
   call, no retrieval, no agent-loop LLM call, no database hit. Disabled
   via `OOS_ENABLED=false`.
3. **Backend → LangChain app layer** — `chat_service` delegates to a
   single `AgentExecutor` (`langchain_app.agent`) built over one prompt
   (`prompts.py`) and N tools: `sql_tools` (`answer_with_sql`/
   `sql_db_schema`) and one `retrieval_tool` (FAISS retriever over
   `embedding/` knowledge-base docs) are always registered, plus — when
   `FIXED_TOOLS_ENABLED=true` (the default) — 16 `business_tools` (one
   per business function, `StructuredTool` wrapping a `database.dao`
   call). One agent, one endpoint — no separate RAG-vs-function-calling-
   vs-SQL path; a single turn can freely mix all three.
4. **Agent decides**: the LLM (`llm.py`'s `ChatOpenAI`, via `get_llm()`)
   either replies with a final answer directly, or calls one or more
   tools:
   - a fixed **business tool** hits `database.dao` (→ PostgreSQL);
   - the **retrieval tool** hits the shared FAISS vector store (→
     `embedding/` docs) for a schema/SQL background answer;
   - **`answer_with_sql`** (only when no fixed tool's shape matches the
     question — see `prompts.py`'s tool-routing rule) hands the question
     to `sql_graph.py`'s own generate → validate → execute loop, which
     runs to completion (success or a bounded-retry failure) inside this
     one tool call — see
     [§ Dynamic SQL Generation](#dynamic-sql-generation-langgraph-sub-graph)
     below.
5. Tool results are captured in `AgentExecutor`'s `intermediate_steps` and
   fed back to the LLM until a final plain-text answer is produced.
6. `table_sources.get_source_tables_for_steps(intermediate_steps)` maps the tool
   calls made this turn back to the DB table(s) they queried; `chat_service`
   returns this alongside the answer as `source_tables` for UI attribution.
   `chart_data.extract_chart_data()` runs the same intermediate steps
   through a deterministic (no-LLM) chart-worthiness heuristic for the UI.
7. `insight_service` / `recommendation_service` reuse the same `llm.get_llm()`
   factory (different prompts) against the last tool-call result, without
   going through the agent's tool-calling loop.

## Dynamic SQL Generation (LangGraph sub-graph)

`answer_with_sql` is always registered (regardless of
`FIXED_TOOLS_ENABLED`) and handles questions no fixed business tool's
shape covers — e.g. a plain "list all X" with no ranking implied, or a
join no fixed tool anticipated. Internally it runs `sql_graph.py`'s
compiled `StateGraph`:

```
discover_schema -> generate_sql -> validate_sql -> execute_sql -> done
                        ^               |                |
                        |   (invalid,   |    (DB error,   |
                        +---attempt<max-+ ----attempt<max-+
```

- **`discover_schema`** builds per-question context via
  `sql_context.build_sql_generation_context()`: a live-reflected
  structural floor (`sql_db.get_sql_database().get_table_info()`) plus
  semantically retrieved business context (the shared FAISS index, see
  below) for *this specific question* — not a fixed schema dump reused
  every turn.
- **`generate_sql`** is its own dedicated LLM call, grounded in that
  context; a prior failed attempt's error is fed back in on retry.
- **`validate_sql`** (`sql_validation.py`) is a deterministic safety
  gate — single statement, `SELECT`/`WITH` only, no DML/DDL keywords,
  mandatory `LIMIT` (capped at `SQL_AGENT_MAX_ROWS`).
- **`execute_sql`** runs through `sql_db.get_execution_sql_database()`
  — a *separate* SQLAlchemy engine over `readonly_pool.py`'s restricted,
  SELECT-only DB role, so a bug in application-level validation is not
  the only thing standing between generated SQL and a write.
- Both `validate_sql` and `execute_sql` retry back to `generate_sql`
  (bounded by `SQL_AGENT_MAX_RETRIES`) before giving up — the whole
  loop resolves inside one outer agent tool call.

Full component/config detail:
[`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md).

## Embedding / RAG Architecture

One FAISS index (`vectorstore/store.py`), built from `embedding/db_diagrams.md`
and `embedding/sample_sqls.md` (chunked one topic per `##`/`#` header,
embedded via `vectorstore/embeddings.py`'s `HuggingFaceEmbeddings`,
persisted with a source-content hash so edits trigger an automatic
rebuild) — with **two independent consumers**, not two indexes:

| Consumer | File | `k` | Feeds |
|---|---|---|---|
| `search_knowledge_base` tool | `tools/retrieval_tool.py` | 3 (fixed) | Conversational schema/SQL background Q&A |
| SQL-generation context | `sql_context.py` | `SQL_CONTEXT_RETRIEVAL_K` (default 4) | `sql_graph.py`'s `generate_sql` prompt |

The same "profit margin formula" chunk, for example, backs both "explain
how margin is calculated" (retrieval tool) and "generate SQL that
calculates margin correctly" (SQL generation) — one index, reused, per
[`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md)
§5's design decision to not stand up a second, generation-specific
index.

## Notes

- **`langchain_app/llm.py`** is the only place `ChatOpenAI` is constructed —
  one place to keep the gateway workarounds (`OPENAI_BASE_URL`,
  `httpx.Client(verify=False)`, per-call random `seed` to defeat the shared
  gateway's response caching) correct, instead of duplicating them per call
  site.
- **`langchain_app/tools/business_tools.py`** is the seam between the agent
  (tool schemas the model sees) and the database layer (DAO calls) — the
  fixed tools never let the model write SQL. **`sql_tools.py`** is the one
  place that does, and only inside the safety-gated, retry-bounded graph
  described above — the outer tool-calling model never authors SQL directly
  as a tool argument.
- Conversation state is in-memory (`chat_service._conversations`), guarded
  by a per-conversation `threading.Lock` — no persistence across process
  restarts (same tradeoff as the additive-plan implementation, sufficient
  for a workshop demo).
