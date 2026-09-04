# embedding/

Knowledge-base source documents indexed into the FAISS vector store
(`langchain_app/vectorstore/store.py`): DB schema description, sample SQL
queries. Retrieved via `langchain_app.tools.retrieval_tool` alongside the
business tools in the same agent turn.

| File | Purpose |
|---|---|
| `db_diagrams.md` | ERD, one `##` section per table (business meaning, relationship semantics — not just column/type lists, which live reflection already covers) and one `##` section per business metric formula, plus a "which query maps to which table(s)" cheat sheet. |
| `sample_sqls.md` | SQL idioms not obvious from schema alone (NULLIF division-by-zero guard, LEFT JOIN for zero-activity dimension rows, date_trunc trend bucketing, LAG-based growth comparison) — narrowed from a full set of example queries once the SQL agent could generate its own. |

Both are chunked by markdown header (`##`/`#`) when indexed — see
`langchain_app/vectorstore/store.py`'s `load_documents()`. Content is
deliberately authored **one topic per `##` section** (one table, one
metric, one idiom) so retrieval returns a focused chunk instead of a
large mixed one — `###` (level-3) headers do not create a new chunk
boundary under the current chunking regex.

This same FAISS index backs two consumers: `tools/retrieval_tool.py`
(background Q&A, `search_knowledge_base`) and
`langchain_app/sql_context.py` (per-question business context fed into
SQL generation) — one index, shared, not duplicated.

**Status:** content matches the actual schema in
`database/scripts/schema.sql` — column names throughout are
`unit_price`/`unit_cost`/generated `revenue`/`profit`, not generic
placeholders.
