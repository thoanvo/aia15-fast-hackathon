# Project Structure

Companion to [`04_solution_design.md`](04_solution_design.md)
(architecture rationale) and [`10_implementation_guide.md`](10_implementation_guide.md)
(phase-by-phase build steps). This doc is the single, authoritative map
of what lives where — `04_solution_design.md` used to carry its own copy
of this tree and now links here instead, so there is exactly one place
this drifts out of date, not two.

## Project structure

```
workshop04/
├── README.md
├── requirements.txt
├── .env.example
│
├── docs/                               — numbered by reading order, see docs/README.md
│   ├── 00_workshop04_task_list.md         — Module/Task/PIC build checklist
│   ├── 01_business_requirements.md       — inherited domain description (Phase 2 scope activated)
│   ├── 02_test_cases_database_query_assistant.md — TC-01..58 business-question test cases + demo questions
│   ├── 03_functional_and_out_of_scope_requirements.md — FR/NFR + hybrid OOS detection spec
│   ├── 04_solution_design.md              — architecture decisions + Phase 0-8 build plan (this repo's own build-out)
│   ├── 05_system_architecture.md          — layered architecture diagram (backend -> langchain_app -> database), OOS gate, dynamic-SQL path
│   ├── 06_database_design.md              — DB schema ERD + agent/tool request-flow diagrams
│   ├── 07_database_schema_reference.md    — table/column reference, metric formulas, seed data
│   ├── 08_project_structure.md            — this doc
│   ├── 09_environment_setup_guide.md      — setup + troubleshooting
│   ├── 10_implementation_guide.md         — phase-by-phase build guide
│   ├── 11_api_documentation.md            — every backend route
│   └── 12_embedding_driven_sql_architecture.md — dynamic-SQL + embedding/RAG architecture deep dive
│
├── src/
│   ├── app.py                         — FastAPI composition root
│   ├── dev_fake_backend.py            — DEV-ONLY: same app, database.dao.* monkeypatched to in-memory data (no real DB needed; LLM still real)
│   ├── dev_fake_sql_engine.py         — DEV-ONLY: in-memory SQLite standing in for Postgres, for the dynamic-SQL agent path specifically (it bypasses database.dao entirely, so dev_fake_backend.py's function-level mocking doesn't cover it)
│   ├── config/
│   │   └── settings.py                — env var loading (DATABASE_URL, OPENAI_*, VECTOR_STORE_*, SQL_AGENT_*)
│   │
│   ├── database/                      — schema, DAO layer, connection pool
│   │   ├── connection/
│   │   │   ├── connection_pool.py
│   │   │   └── readonly_pool.py        — separate, restricted-role engine for the dynamic-SQL agent's execution step, independent of application-level SQL validation
│   │   ├── dao/{product,customer,sales,region,analytics}_dao.py
│   │   ├── scripts/{schema.sql,init_db.py}
│   │   └── mock_data/sample_data.sql
│   │
│   ├── backend/                       — thin service/controller layer
│   │   ├── controllers/chat_controller.py      — single /api/v1/chat endpoint
│   │   ├── models/{conversation,message}.py     — Message carries chart_data alongside source_tables/kb_chunks/tool_results
│   │   └── services/
│   │       ├── chat_service.py                 — conversation store + locking, delegates to langchain_app/
│   │       ├── insight_service.py                — generic over any tool result shape, fixed-tool or dynamic-SQL alike
│   │       └── recommendation_service.py
│   │
│   ├── langchain_app/                 — the LangChain-native AI/function-calling core
│   │   ├── llm.py                     — ChatOpenAI factory: gateway compat + per-call random seed
│   │   ├── prompts.py                 — ChatPromptTemplate: scope rules, refusal behavior, few-shot examples
│   │   ├── agent.py                   — create_tool_calling_agent + AgentExecutor construction
│   │   ├── oos_guard.py               — hybrid out-of-scope detection: intent classification + similarity threshold, runs before the agent
│   │   ├── table_sources.py           — tool name -> DB table(s) mapping (UI attribution); the dynamic-SQL tool derives this from its executed query instead of a static entry
│   │   ├── sql_db.py                  — SQLDatabase factories: schema reflection (main engine) and execution (restricted engine)
│   │   ├── sql_validation.py          — deterministic single-statement/SELECT-only/mandatory-LIMIT gate before any generated SQL executes
│   │   ├── sql_context.py             — per-question SQL-generation context: live schema reflection plus semantic retrieval over the same FAISS index search_knowledge_base uses
│   │   ├── sql_graph.py               — LangGraph state graph for the dynamic-SQL path: discover schema -> generate SQL -> validate -> execute, with a bounded retry that feeds the failing error back into the next generation attempt
│   │   ├── chart_data.py              — deterministic (no extra LLM call) chart-worthiness heuristic over a turn's tool results
│   │   ├── vectorstore/
│   │   │   ├── embeddings.py          — embedding function (single source of truth, no dual-path risk)
│   │   │   └── store.py               — FAISS vectorstore setup + sync from embedding/ docs; auto-rebuilds when the source content's hash no longer matches the persisted index
│   │   └── tools/
│   │       ├── business_tools.py      — StructuredTool wrappers over DAO-backed handlers - gated by FIXED_TOOLS_ENABLED, default true
│   │       ├── retrieval_tool.py      — @tool wrapping the vectorstore retriever
│   │       └── sql_tools.py           — sql_db_schema (on-demand column lookup) and the dynamic-SQL tool (takes the user's question, runs sql_graph.py, returns rows) - always registered, not gated by a flag
│   │
│   ├── embedding/                     — knowledge-base source docs (one table/metric/SQL-idiom per section) to index; shared by search_knowledge_base and sql_context.py, not duplicated
│   │
│   ├── frontend/                      — Streamlit multipage UI
│   │   ├── app.py                     — st.navigation entry point
│   │   ├── api_client.py              — send_message() also returns chart_data alongside the answer/source_tables/kb_chunks
│   │   ├── pages/{home,chat}.py
│   │   └── components/{chat_interface,response_display,conversation_history}.py — response_display.render_data_chart() renders chart_data via Streamlit's built-in line/bar charts
│   │
│   └── tests/{unit,integration,end_to_end}/
```

## Layering rule

Dependencies point one direction only:

```
frontend  -->  backend  -->  langchain_app  -->  database
```

`frontend/` never calls `database/` or `langchain_app/` directly — only
through the backend's HTTP API. `langchain_app/` never imports from
`backend/` — the agent and its tools are backend-agnostic; `backend/`
depends on `langchain_app/`, not the other way around. The dynamic-SQL
path (`sql_db.py`, `sql_graph.py`) follows the same rule: it imports from
`database.connection.*` for its engines, never the reverse.

## Status

See each `src/` subfolder's own `README.md` for per-folder implementation
status, and [`10_implementation_guide.md`](10_implementation_guide.md) for the
phase checklist. Phases 0 (environment/scaffolding), 1 (database & DAO layer), 2 (vector
store & embeddings), 3 (LangChain tools), 4 (LangChain agent), 5 (service
& controller layer), 6 (frontend), and 8 (documentation) are done; Phase 7
(a formal `pytest` suite) is still open — every phase so far was verified
with ad-hoc scripts, not a committed test suite. Note: Phases 4-6 were
verified against a scripted fake chat model, not a real OpenAI-compatible
endpoint — no gateway credentials were available in this environment.

Three later phases, done and unit-tested, extended this structure beyond
the original Phase 0-8 build-out: **Phase 9** added a schema-aware
dynamic-SQL path (`sql_db.py`, `sql_validation.py`,
`tools/sql_tools.py`, `database/connection/readonly_pool.py`) alongside
the 16 fixed business tools, gated off by default behind
`SQL_AGENT_ENABLED` until a dedicated read-only DB role is provisioned.
**Phase 10** routed semantic retrieval into that SQL-generation path
(`sql_context.py`), restructured it as an explicit LangGraph state graph
(`sql_graph.py`), added chart-data extraction for the frontend
(`chart_data.py`), and confirmed insight/recommendation generation
already generalizes to dynamic-SQL results unchanged. **Phase 11**
(HACK-B03) replaced `SQL_AGENT_ENABLED` with `FIXED_TOOLS_ENABLED`
(default `true`) and inverted which side it gates: the dynamic-SQL
tools are now always registered, and the flag instead controls the 16
fixed business tools. See [`04_solution_design.md`](04_solution_design.md)
for the full rationale behind all three phases.

See [`01_business_requirements.md`](01_business_requirements.md)'s "Future
Enhancements" section for the next phase beyond this repo's own build-out.
