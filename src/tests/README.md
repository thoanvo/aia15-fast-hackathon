# tests/

- `unit/` — DAO functions, `business_tools.py` wrapping, `table_sources.py` mapping
- `integration/` — `TestClient` + fake-DB harness (DAO layer swapped for in-memory sample data), full chat turns incl. follow-up
- `end_to_end/` — the example conversation from `01_business_requirements.md` end to end

**Status:** unit tests implemented; integration and end-to-end tests remain — see Phase 7 in
[`../../docs/04_solution_design.md`](../../docs/04_solution_design.md).

## Run unit tests

From the repository root after installing `requirements.txt`:

```powershell
cd src
python -m pytest tests/unit
```

The unit suite uses fake LLMs, fake executors, and monkeypatched DAO/retriever
calls. It does not require a reachable database, OpenAI credentials, a FAISS
index, or network access.

Covered unit slices include domain models, table-source attribution, business
tool wrappers, RAG result formatting, out-of-scope decisions, agent
orchestration, conversation state, and insight/recommendation adapters.
