# langchain_app/

The LangChain-native AI/function-calling core — the one thing this repo
does differently from the additive `workshop03` implementation. No legacy
bespoke AI layer to parallel; this is the only path.

- `llm.py` — `ChatOpenAI` factory: gateway `base_url`/`http_client` compat + per-call random `seed` override (single source of truth, used by the agent and, later, by insight/recommendation generation) — **done**
- `prompts.py` — `ChatPromptTemplate`: scope rules, refusal behavior, few-shot examples; also holds `INSIGHT_PROMPT`/`RECOMMENDATION_PROMPT` for Phase 5 — **done**
- `agent.py` — `create_tool_calling_agent` + `AgentExecutor` construction; `intermediate_steps` → `source_tables` via `run_turn()`; calls `oos_guard.check_scope()` before the agent runs at all — **done**
- `oos_guard.py` — hybrid out-of-scope detection (intent classification + embedding-similarity threshold), per `docs/03_functional_and_out_of_scope_requirements.md`; fails open on error — **done**
- `table_sources.py` — tool name -> DB table(s) mapping (UI attribution) — **done**
- `vectorstore/embeddings.py` — `HuggingFaceEmbeddings` factory (single source of truth, no dual-path embedding-mismatch risk) — **done**
- `vectorstore/store.py` — FAISS index build/sync/persist from `embedding/` — **done**
- `tools/business_tools.py` — `StructuredTool` per business function, wrapping `database.dao` calls (16 tools) — **done**
- `tools/retrieval_tool.py` — `@tool` wrapping the FAISS retriever — **done**

**Status:** Phases 2-4 (vector store & embeddings, tools, agent) all done —
see [`../../docs/04_solution_design.md`](../../docs/04_solution_design.md).
`agent.py` accepts `llm`/`tools` overrides (dependency injection) for
exactly this reason: it was verified end-to-end (tool calling, batching,
refusal path, multi-turn `chat_history`, `source_tables` extraction)
against a scripted `FakeMessagesListChatModel`, without needing a real
OpenAI-compatible endpoint or API key — see `agent.py`'s docstring.
`llm.py`'s real `ChatOpenAI` construction was verified separately (no
network call happens at construction time). Business logic (what each
tool computes) was ported from the prior implementation's handler logic —
only the wrapping (`@tool`/`StructuredTool` instead of a hand-rolled JSON
schema + registry/executor) changed. See `tools/README.md` for a
Windows-specific import-order gotcha discovered while wiring
`business_tools` and `retrieval_tool` into the same process.

`oos_guard.py` was verified with real embeddings (empirically calibrating
`OOS_SIMILARITY_THRESHOLD` against real in-scope/out-of-scope test
questions - see its module docstring) and a scripted fake classifier LLM
(same DI pattern as `agent.py`'s `llm`/`tools` overrides, via `run_turn()`'s
`oos_llm` parameter): confirmed an out-of-scope question never reaches the
agent (no tool call, no agent LLM call), an in-scope question passes
through unaffected, and a broken classifier fails open instead of blocking
the turn. Real-world classification accuracy (NFR: >90%) still needs real
LLM credentials to measure.
