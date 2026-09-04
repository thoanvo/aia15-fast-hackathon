# langchain_app/tools/

LangChain tools passed to the agent (Phase 4) — business data tools plus
one RAG retrieval tool, so a single agent turn can freely mix both.

- `business_tools.py` — 16 `@tool`-decorated functions (LangChain infers a
  `StructuredTool` from the type hints; `parse_docstring=True` gives each
  parameter its own description from the Google-style `Args:` section),
  one per Core Business Function, wrapping `database.dao` calls. Every
  tool body runs through `_safe()`, which catches bad-argument
  (`ValueError`, e.g. `limit` out of `1..100`) and DB errors and returns
  `{"error": "..."}` instead of raising, so one bad call doesn't crash the
  whole agent turn.
- `retrieval_tool.py` — `search_knowledge_base`, a `@tool` wrapping
  `langchain_app.vectorstore.store.get_retriever()`. Same graceful-error
  handling as the business tools.

## Import order matters here (Windows)

`retrieval_tool` lazily loads `sentence-transformers` (torch) only when an
embedding is actually computed; `business_tools` eagerly loads
SQLAlchemy's compiled Cython extensions (`sqlalchemy.cyextension.*`) at
import time. If those load into the process before torch does, torch's
own DLL loading fails:

```
OSError: [WinError 1114] ... c10.dll ...
```

This is the same category of issue as the plan doc's documented
torch-vs-onnxruntime DLL load-order quirk, just a different pairing
(discovered while wiring both tool modules into the same process for the
first time here in Phase 3). The fix lives in `__init__.py`: importing
this package forces the embedding model to load first, before Python can
reach the `business_tools` submodule. **Always import tools through this
package** (`from langchain_app.tools.business_tools import ...` /
`from langchain_app.tools.retrieval_tool import ...` — either one triggers
`__init__.py` first) rather than reaching into `database.dao` directly in
a process that also needs the retrieval tool.

**Status:** Phase 3 done — 16 business tools + 1 retrieval tool, verified
with a real (mocked-DB) smoke test.
