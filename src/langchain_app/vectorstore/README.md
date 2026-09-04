# langchain_app/vectorstore/

FAISS-backed RAG vector store over `../../embedding/` knowledge-base docs.

- `embeddings.py` — `get_embeddings()`: single cached `HuggingFaceEmbeddings`
  instance (`EMBEDDING_MODEL_NAME` from `config.settings`, default
  `sentence-transformers/all-MiniLM-L6-v2`). Single source of truth so the
  index is never built with one embedding function and queried with
  another.
- `store.py` — `get_vectorstore()` / `get_retriever()`: loads the persisted
  FAISS index from `VECTOR_STORE_DIR` if present, otherwise builds it from
  `embedding/` (chunked by markdown header) and persists it. Pass
  `force_rebuild=True` after editing `embedding/` docs.

FAISS is used instead of Chroma specifically to avoid `onnxruntime` as a
transitive dependency (Chroma's default embedding path pulls it in),
sidestepping the Windows torch-vs-onnxruntime DLL load-order issue by
construction. The index directory itself (`VECTOR_STORE_DIR`, default
`langchain_app/vectorstore/index/`) is git-ignored — it's a build artifact,
rebuildable from `embedding/` at any time.

**Status:** Phase 2 complete.

```python
from langchain_app.vectorstore.store import get_retriever

retriever = get_retriever(k=3)
docs = retriever.invoke("How is profit margin calculated?")
```
