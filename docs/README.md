# docs/

Documentation for the Database Query Assistant (Hackathon, LangChain-native
implementation). See [`../README.md`](../README.md) for the actual
application code and how to run it.

## Reading order

| # | Document | Category | Purpose |
|---|---|---|---|
| 00 | [`00_workshop04_task_list.md`](00_workshop04_task_list.md) | Development | Module/Task/PIC checklist covering the original Hackathon build-out (`Refactor:` tasks, one row per module) plus the later Dynamic SQL Agent enhancement tasks; PIC column left blank for team assignment. |
| 01 | [`01_business_requirements.md`](01_business_requirements.md) | Planning & Requirements | Full business context: problem statement, target users, scope, core business functions, example conversation, success criteria, current implementation status, and future enhancements. **Start here.** |
| 02 | [`02_test_cases_database_query_assistant.md`](02_test_cases_database_query_assistant.md) | Development | TC-01..94 business-question test cases across 12 categories (basic queries, product/customer/sales/region analytics, insight/recommendation, follow-up conversation, RAG/KB questions, dynamic SQL agent, negative/safety testing, fixed-tool coverage, fixed-tool feature-flag routing), plus a demo-question list. |
| 03 | [`03_functional_and_out_of_scope_requirements.md`](03_functional_and_out_of_scope_requirements.md) | Analysis & Design | Functional + non-functional requirements for a hybrid out-of-scope detection strategy (intent classification + similarity threshold + LLM guardrails). **Implemented** in `src/langchain_app/oos_guard.py`. |
| 04 | [`04_solution_design.md`](04_solution_design.md) | Analysis & Design | Solution design: architecture decisions and the Phase 0-8 build plan that produced this repo. Read this for *why* the structure looks the way it does. Project structure itself now lives only in `08` (not duplicated here). |
| 05 | [`05_system_architecture.md`](05_system_architecture.md) | Analysis & Design | Layered architecture diagram (backend → langchain_app → database), the OOS gate, the dynamic-SQL tool path (`sql_graph.py`'s generate/validate/execute loop), and the shared embedding/RAG index — see `12` for the full detail behind the latter two. |
| 06 | [`06_database_design.md`](06_database_design.md) | Analysis & Design | Database ERD and the agent/tool request-flow diagram for one chat turn. |
| 07 | [`07_database_schema_reference.md`](07_database_schema_reference.md) | Analysis & Design | Table/column reference, key metric formulas, seed-data summary. |
| 08 | [`08_project_structure.md`](08_project_structure.md) | Development | The single, authoritative map of what lives in each `src/` subfolder and the layering rule. |
| 09 | [`09_environment_setup_guide.md`](09_environment_setup_guide.md) | Development | End-to-end environment setup + a troubleshooting section covering every real issue hit building this. |
| 10 | [`10_implementation_guide.md`](10_implementation_guide.md) | Development | Phase-by-phase build guide: files, steps, dependencies, acceptance checks per phase. |
| 11 | [`11_api_documentation.md`](11_api_documentation.md) | Development | Every backend route, request/response shapes, error behavior. |
| 12 | [`12_embedding_driven_sql_architecture.md`](12_embedding_driven_sql_architecture.md) | Analysis & Design | High-level architecture of the embedding-driven dynamic-SQL path: FAISS ingestion pipeline, the `sql_graph.py` LangGraph generation pipeline, the shared-index-two-consumers decision, and config reference. |

## Dependencies between documents

```
01 (business requirements) ──┬──> 04 (solution design) ──┬──> 05 (system architecture) ──> 06 (database design) ──> 07 (schema reference)
                              │                            │                                                              │
                              │                            ├──> 08 (project structure) ──> 09 (setup) ──> 10 (implementation guide) ──> 11 (API docs)
                              │                            └──> 00 (task list)
                              └──────────────────────────────────────────────────────────────────────────────────────────> 02 (test cases)
03 (OOS requirements) ─────────────────────> implemented in src/langchain_app/oos_guard.py, referenced from 05's request flow
05 (system architecture) ─────────────────> 12 (embedding-driven SQL architecture) — 05 stays at the layered-overview level, 12 is the full detail
```

In prose: 01 is the one requirement input everything else traces back to.
04 is the design that resulted from it; 05-11 are that design realized as
an actual system, in the order a developer would build/read it. 00 is the
flattened task-checklist view of 04's build plan. 02 is the
business-question test set used to verify the built system against 01's
scope. 03 is a standalone requirements doc, implemented directly in code
(`oos_guard.py`) rather than through the 04→05 chain. 12 is a deep-dive on
the one subsystem (dynamic SQL + embeddings) that 05 only summarizes.

## Not part of the numbered sequence

- Root [`../README.md`](../README.md) — quick start, tech stack table,
  project status, and its **own** TC-01..13 test cases (API-level smoke
  tests: health checks, request validation, OOS refusal, etc.) — a
  different set from `02`'s TC-01..58 business-question test cases
  despite the shared "TC-" numbering; don't confuse the two. This
  `docs/` sequence is for *understanding* the system; the root README is
  the entry point for *running* it.
- Each `src/` subfolder's own `README.md` — implementation-level detail
  and per-folder status notes, referenced throughout 08-11 above.
