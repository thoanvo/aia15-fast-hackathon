# Hackathon — Greenfield Repo Plan (Big Picture)

If Hackathon were built as its **own repo from zero** (`workshop04/`), rather than
additively on top of the existing `workshop03` codebase (an alternative
approach considered and set aside — those comparison docs are no longer
present in this repo), this is the project structure, architecture, and
task breakdown it would need — informed by the RAG/vector-store/LangChain/
function-calling requirements and the business domain in
[`01_business_requirements.md`](01_business_requirements.md).

## Big picture

**Hackathon is not a new business problem — it's Phase 2 of the existing one.**
`01_business_requirements.md`'s own "Future Enhancements > Phase 2" section
(written for Workshop 2) already lists exactly what Hackathon asks for:
*"RAG (Retrieval Augmented Generation)", "Vector Database Integration",
"Embeddings", "LangChain Integration", "LangGraph Support"*. So a greenfield
Hackathon repo keeps the **same business domain** (the Database Query
Assistant: products/customers/sales/regions, the same 16 core business
functions, the same target personas and success criteria) and rebuilds the
**AI/function-calling layer LangChain-native from day one**, instead of the
custom hand-rolled OpenAI SDK loop the original implementation used.

What carries over unchanged (same domain, same schema, same functions):
database schema, DAO layer, the 16 business functions, target personas,
example conversation, success criteria.

What's rebuilt LangChain-native instead of retrofitted:
the AI/function-calling layer (`backend/ai/` + `backend/function_calling/`
in the old repo) becomes a single `langchain_app/` package — no bespoke
OpenAI tool-calling loop to maintain, no "does this parallel the native
path" question, because there's only one path.

What's carried over as **lessons learned**, not code (see the additive
plan's "Why not..." sections for the reasoning), baked in from the start
instead of retrofitted:
- Vector store choice is a `langchain_community`/`langchain-chroma` or
  `langchain-community` FAISS wrapper **used as the primary interface**
  (not bypassed like the additive plan had to, since there's no
  precomputed-embedding legacy collection to stay compatible with) —
  embeddings and vector store are the same LangChain-managed pipeline from
  day one, so there's no embedding-function-mismatch risk to design around.
- Gateway compatibility (`OPENAI_BASE_URL`, `httpx.Client(verify=False)`
  when going through the workshop's shared proxy) and the random-`seed`
  per-call cache-busting workaround are still required — the shared
  gateway's caching quirk is an environment fact, not an artifact of the
  old codebase, so `ChatOpenAI` still needs the same `_generate()`-override
  pattern.
- Windows torch-before-onnxruntime DLL load order still applies if
  `sentence-transformers` and `chromadb`/`onnxruntime` are both used —
  design the vector-store choice (FAISS avoids `onnxruntime` entirely if
  using a non-onnx embedding backend) with this in mind up front rather
  than discovering it mid-project. **Choosing FAISS doesn't eliminate this
  whole category of bug, though** — Phase 3 hit a sibling issue on this
  same environment (Windows/Python 3.13): SQLAlchemy's compiled Cython
  extensions (`sqlalchemy.cyextension.*`, loaded eagerly by
  `database.dao`/`connection_pool` at import time) poison torch's DLL
  loading (`sentence-transformers`, loaded lazily by `HuggingFaceEmbeddings`
  only when an embedding is actually computed) if the SQLAlchemy import
  wins the race — same `OSError: [WinError 1114] ... c10.dll ...` symptom,
  different pairing. Fixed in `langchain_app/tools/__init__.py` by forcing
  the embedding model to load at package-import time, before Python can
  reach the `business_tools` submodule (and therefore SQLAlchemy) — see
  that file's docstring and `tools/README.md`.
- A single unified LangChain tool-calling agent (retrieval tool + business
  tools) beats splitting retrieval and function-calling into two chains —
  same reasoning as the additive plan: one turn should be able to freely
  mix both, matching how the business domain's own example conversation
  ("top 5 products" → "Only in Asia." → "insights") interleaves data
  retrieval and reasoning in a single thread.
- `source_tables`-style UI attribution (which DB table an answer came from)
  is worth building in from the start as a first-class concept, not
  bolted on later — it directly serves the "Clarity" success criterion in
  `01_business_requirements.md`.

See [`08_project_structure.md`](08_project_structure.md) for the current,
authoritative project structure (single source of truth — not duplicated
here to avoid the two copies drifting apart).

## Architecture decisions

1. **One agent, one endpoint.** `POST /api/v1/chat` is the only chat
   endpoint — no need for `/chat` vs `/rag/chat` vs `/langchain/chat` as
   parallel surfaces, since there's nothing to keep backward-compatible.
   `langchain_app/agent.py` builds a single `AgentExecutor` over N tools
   (business functions + retrieval), same reasoning as the additive plan's
   "One unified LangChain tool-calling agent" decision.
2. **Vector store: FAISS via `langchain-community`, in-process, no external
   service.** Matches the workshop's "any vector store" allowance, avoids
   provisioning an external Pinecone account, and — unlike Chroma bundling
   `onnxruntime` — FAISS with a `sentence-transformers`-backed
   `HuggingFaceEmbeddings` keeps the dependency footprint to `torch` only,
   sidestepping the Windows DLL-order issue entirely rather than working
   around it.
3. **Conversation memory**: same in-memory `dict[conversation_id, Conversation]`
   + per-conversation `threading.Lock` pattern proven in the additive plan
   — simple, sufficient for a workshop demo, and the existing pattern
   already handles the FastAPI-threadpool concurrency concern correctly.
4. **`source_tables` attribution**: built directly into `agent.py`'s result
   handling (via `intermediate_steps` + `table_sources.get_source_tables()`)
   from the first implementation, not added after the fact.
5. **Gateway/seed compatibility**: `langchain_app/llm.py` exports a single
   `get_llm()` factory used everywhere an LLM call is needed (agent,
   insight generation, recommendation generation) — one place to keep the
   gateway workarounds correct, instead of duplicating `ChatOpenAI`
   construction per call site.
6. **Dynamic SQL as additive tools, not a second agent (Phase 9).** Given
   decision 1's "one agent, one endpoint," the SQL-agent path is two more
   tools (`sql_db_schema`, `answer_with_sql`) on the same `AgentExecutor`,
   not a parallel `create_sql_agent`-style agent. A sub-agent would add a
   second LLM-loop boundary (its own iteration/timeout budget, its own
   error surface) for no benefit at this schema's size (4 tables) — worth
   reconsidering only if the tool list grows much larger.
7. **Two safety layers for generated SQL, not one (Phase 9).**
   `sql_validation.py`'s deterministic SELECT-only/single-statement/LIMIT
   gate (application layer) and a separate, restricted read-only DB role
   (`database/connection/readonly_pool.py`, database layer) are
   independent controls — a bug in the first must not be the only thing
   standing between generated SQL and a write/DDL operation. Default
   `SQL_AGENT_ENABLED=false` until the DB role is actually provisioned in
   a given environment (the app-level gate alone isn't considered
   sufficient to enable by default). **Superseded in Phase 11** — the
   dynamic-SQL tools are now always registered (no flag gates them at
   all), so these two layers are the *only* thing standing between
   generated SQL and a write/DDL operation in every environment, not just
   ones that opted in. Provisioning `READONLY_DATABASE_URL` before going
   live is no longer optional-by-flag; see Phase 11 below.
8. **`answer_with_sql` takes the question, not SQL the model writes
   (Phase 10).** Originally (Phase 9) the outer tool-calling model
   authored SQL directly as a tool argument, retried by calling the tool
   again (bounded by a per-turn attempt counter). Once the SQL path
   became a LangGraph sub-graph (decision 9), SQL authorship moved
   *inside* the tool — to the graph's own `generate_sql` node, grounded
   in schema context the graph gathers itself — so the outer model only
   ever passes along the user's natural-language question. This let two
   things be retired outright: the outer-level attempt counter
   (superseded by the graph's own internal bounded retry) and the
   `{schema_context}` prompt-injection mechanism (the outer model no
   longer needs schema knowledge of its own).
9. **LangGraph for the SQL sub-path only, not the whole agent (Phase 10).**
   `sql_graph.py`'s `discover_schema -> generate_sql -> validate_sql ->
   execute_sql` graph (bounded retry back to `generate_sql`, the failing
   error fed into the next attempt) replaces the implicit tool-calling
   loop for exactly the SQL path — the fixed 16 tools + retrieval stay on
   the plain `AgentExecutor`. Same "smaller blast radius" reasoning as
   decision 6: a full-agent graph rewrite is only worth it if the
   fixed-tool path also needs explicit multi-step control flow.
10. **Retrieval augments reflection, it doesn't replace it (Phase 10).**
    `sql_context.py` always includes a live-reflected structural floor
    (table/column list) alongside retrieved business context (table
    descriptions, relationships, metric formulas — from the *same* FAISS
    index `search_knowledge_base` already used, re-chunked one topic per
    `##` section for retrieval precision, not a second index). Reflection
    guarantees structural correctness for free; at a 4-table schema,
    dropping it in favor of retrieval-only would risk an incomplete
    retrieved subset for no benefit.

## Tasks List

Phased like the original `10_implementation_guide.md`, since the domain and
early layers are unchanged — LangChain-specific work starts at Phase 3.

### Phase 0 — Environment & scaffolding
- [x] Repo init, `requirements.txt` (fastapi, uvicorn, streamlit, sqlalchemy, psycopg2-binary, python-dotenv, pydantic, langchain-core, langchain-classic, langchain-openai, langchain-community, faiss-cpu, sentence-transformers, pytest)
- [x] `config/settings.py` — env var loading + fail-fast validation
- [x] `.env.example`, `README.md` skeleton

### Phase 1 — Database & DAO layer
- [x] `database/scripts/schema.sql` + `init_db.py` (products, customers, sales, regions)
- [x] `database/mock_data/sample_data.sql` (matches the business description's example conversation numbers)
- [x] `database/dao/*.py` — one module per table/aggregate area (product/customer/sales/region/analytics)
- [x] `database/connection/connection_pool.py`

### Phase 2 — Vector store & embeddings
- [x] `embedding/` — author knowledge-base docs (DB schema description, sample SQL queries)
- [x] `langchain_app/vectorstore/embeddings.py` — `HuggingFaceEmbeddings` factory (single source of truth)
- [x] `langchain_app/vectorstore/store.py` — FAISS index build/sync/persist from `embedding/`

### Phase 3 — LangChain tools
- [x] `langchain_app/tools/business_tools.py` — `StructuredTool` per business function, wrapping DAO calls (16 tools)
- [x] `langchain_app/tools/retrieval_tool.py` — `@tool` wrapping the FAISS retriever
- [x] `langchain_app/table_sources.py` — function name -> DB table(s) mapping

### Phase 4 — LangChain agent
- [x] `langchain_app/llm.py` — `ChatOpenAI` factory: gateway `base_url`/`http_client`, per-call random `seed` override
- [x] `langchain_app/prompts.py` — system prompt (scope rules, refusal behavior for out-of-scope questions, few-shot examples)
- [x] `langchain_app/agent.py` — `create_tool_calling_agent` + `AgentExecutor`, `intermediate_steps` → `source_tables`
  (verified against a scripted fake chat model — no real gateway credentials available in this environment yet)

### Phase 5 — Service & controller layer
- [x] `backend/models/{conversation,message}.py`
- [x] `backend/services/chat_service.py` — conversation store, locking, delegates to `langchain_app.agent`
- [x] `backend/services/{insight,recommendation}_service.py`
- [x] `backend/controllers/chat_controller.py` — `POST /chat`, `GET /chat/{id}/history`, insight/recommendation/clear endpoints
- [x] `src/app.py` — FastAPI composition root
  (verified end-to-end with TestClient + a scripted fake chat model — no real gateway credentials available in this environment yet)

### Phase 6 — Frontend
- [x] `frontend/api_client.py`, `frontend/app.py` (`st.navigation`)
- [x] `frontend/pages/{home,chat}.py`
- [x] `frontend/components/{chat_interface,response_display,conversation_history}.py` (incl. `source_tables` caption rendering)
  (verified with Streamlit AppTest against a real backend with a stubbed LLM — no real gateway credentials available in this environment yet)

### Phase 7 — Testing & mock data
- [ ] `tests/unit/` — DAO functions, `business_tools.py` wrapping, `table_sources.py` mapping
- [ ] `tests/integration/` — `TestClient` + fake-DB harness (mirrors the additive plan's `dev_fake_backend.py` pattern), full chat turns incl. follow-up
- [ ] `tests/end_to_end/` — the example conversation from `01_business_requirements.md` end to end

### Phase 8 — Documentation & presentation deliverables
- [x] `docs/11_api_documentation.md`, `docs/07_database_schema_reference.md`, `docs/09_environment_setup_guide.md`
- [x] Problem statement + mock data schema writeup (Hackathon deliverable) — covered by `01_business_requirements.md` + `07_database_schema_reference.md`, no separate doc needed
- [x] Test cases + conversation examples showcasing the solution (Hackathon deliverable) — root `README.md`'s expanded TC-01..12 table
- [ ] Presentation: architecture walkthrough, live demo, lessons learned — needs a running-app demo/screenshots, not yet produced

### Phase 9 — Dynamic SQL Agent

- [x] `langchain_app/sql_db.py` — `SQLDatabase` factories wrapping the
  existing engine (schema reflection) and a new restricted engine
  (execution) — no second application-level connection pool
- [x] `langchain_app/tools/sql_tools.py` — `sql_db_schema` (on-demand
  column lookup) + the SQL-execution tool, both `_safe()`-wrapped like
  `business_tools.py`
- [x] `langchain_app/sql_validation.py` — deterministic single-statement/
  SELECT-only/mandatory-`LIMIT` gate (`sqlparse`-based) before any
  generated SQL executes
- [x] `database/connection/readonly_pool.py` + `READONLY_DATABASE_URL` —
  separate, restricted-role engine independent of application-level
  validation (falls back to `DATABASE_URL` for local dev only)
- [x] Bounded retry on validation/execution failure (superseded in
  Phase 10 by the LangGraph sub-graph's own internal retry — see
  architecture decision 8)
- [x] `table_sources.py` — SQL-path `source_tables` attribution derived
  from the executed query's `FROM`/`JOIN` clauses, not a static mapping
- [x] `SQL_AGENT_ENABLED` feature flag, default `false` — gates tool
  registration and the prompt wording narrowing; flag-off prompt is
  byte-identical to the pre-Phase-9 wording
  (verified with the existing DI/fake-model unit-test pattern — no real
  DB/LLM required; `sqlparse`/native-extension DLL-load-order confirmed
  safe on this environment before adopting it)
  **— renamed and inverted in Phase 11, see below.**

### Phase 10 — Embedding-Driven Generation, Result Analysis, Visualization, LangGraph

- [x] `langchain_app/sql_context.py` — per-question SQL-generation
  context: live structural reflection + semantic retrieval over the
  *same* FAISS index `search_knowledge_base` already uses (one index,
  two consumers, not a duplicated one)
- [x] `embedding/db_diagrams.md` + `sample_sqls.md` re-authored into one
  `##` chunk per table / per business metric / per SQL idiom (was: a few
  large mixed sections) — verified retrieval precision improved (a
  region-vs-customer-region ambiguity question now retrieves the exact
  disambiguating business rule instead of an unrelated mixed chunk)
- [x] `langchain_app/vectorstore/store.py` — auto-rebuild the FAISS index
  on a source-content hash mismatch, so an edited `embedding/` doc can't
  silently keep serving a stale persisted index
- [x] Result Analysis Agent — verified `insight_service.py`/
  `recommendation_service.py` already generalize to SQL-path
  `tool_results` shapes with zero production-code changes (added
  verification test only)
- [x] `langchain_app/chart_data.py` — deterministic (no extra LLM call)
  chart-worthiness heuristic over a turn's tool results; threaded through
  `agent.py` → `chat_service.py` → `Message`/`chat_controller.py` →
  `frontend/api_client.py` → `response_display.render_data_chart()`
  (Streamlit `st.line_chart`/`st.bar_chart`, no new charting dependency)
- [x] `langchain_app/sql_graph.py` — explicit LangGraph state graph
  (`discover_schema → generate_sql → validate_sql → execute_sql`, bounded
  retry with the failing error fed back into the next generation
  attempt) for the SQL sub-path only, not the whole agent (architecture
  decision 9); confirmed no Windows DLL-load-order conflict from
  `langgraph`'s compiled `ormsgpack` dependency before adopting it
- [x] SQL tool surface simplified to a single question-in, rows-out tool
  once the graph owned schema discovery/generation internally
  (architecture decision 8) — retired the Phase 9 outer-level retry
  counter and the `{schema_context}` prompt-injection mechanism as a
  direct consequence, not separate cleanup
- [x] `dev_fake_sql_engine.py` — in-memory SQLite standing in for
  Postgres specifically for the SQL-agent path (which bypasses
  `database.dao`'s monkeypatching entirely), wired into
  `dev_fake_backend.py`; fixed a SQLite `NUMERIC` integer-division quirk
  that was silently zeroing out every `NULLIF`-guarded margin calculation
  (verified: all of the above with the existing DI/fake-model/fake-DB
  unit-test pattern, plus scripted end-to-end runs against both the real
  FAISS index and the fake SQLite engine — no real DB/LLM credentials
  required for any of it)

### Phase 11 — Fixed Tool Feature Flag (HACK-B03)

Reworked which side of the tool list the feature flag actually gates,
per `plan/HACK-B03_Fixed_Tool_Feature_Flag.md`: the flag now controls
whether the 16 **fixed business tools** are registered, not whether the
**dynamic-SQL tools** are. This is the opposite of Phase 9's original
design (decision 7/Phase 9 above), where the flag gated the dynamic-SQL
tools and the fixed tools were always on.

- [x] `SQL_AGENT_ENABLED` removed, replaced by `FIXED_TOOLS_ENABLED`
  (default `true`) in `config/settings.py` — gates `get_business_tools()`
  only; `get_retrieval_tool()` and `get_sql_tools()`
  (`sql_db_schema`/`answer_with_sql`) are now unconditional in
  `agent.get_tools()`
- [x] `prompts.py`'s flag-keyed variants renamed and re-derived for the
  new split: `_FIXED_AND_DYNAMIC_TOOL_RULE` (both tool sets present,
  the fixed-tool-first decision checklist from Phase 9 unchanged) vs.
  a new `_DYNAMIC_ONLY_TOOL_RULE` (no fixed tools registered — every
  data question routes to `answer_with_sql`) — the old
  `_ORIGINAL_TOOL_RULE` (no dynamic-SQL tools at all) no longer applies
  to any reachable state, since dynamic-SQL is never absent now.
  Same split applied to the broad-request rule/example and the
  first few-shot example (`get_top_products(limit=5)`), which
  previously appeared unconditionally and would have named a
  nonexistent tool when fixed tools are disabled
- [x] `agent.py` trace logging — `_tool_mode()` classifies each tool
  call as `FIXED_TOOL`/`DYNAMIC_SQL`/`RETRIEVAL` for a per-turn routing
  log line, plus a registration-time summary log — added specifically
  so this flag's routing behavior (which mode actually fired) is
  observable at runtime, not just inferable from the prompt
  (verified with the existing DI/fake-model unit-test pattern, plus a
  manual log-output smoke test)

**Security note**: because the dynamic-SQL tools can no longer be
switched off, decision 7's two independent safety layers
(`sql_validation.py`'s app-level gate + `READONLY_DATABASE_URL`'s
restricted DB role) are load-bearing in every environment from first
boot, not just ones that had opted into the old flag. An environment
that hasn't provisioned a dedicated read-only role falls back to
`DATABASE_URL` (full app privileges) for generated-SQL execution — see
`config/settings.py`'s `READONLY_DATABASE_URL` comment.
