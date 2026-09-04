"""LangChain vectorstore - embedding function.

Single source of truth for the embedding model used to both build and
query the FAISS index (`store.py`), so there is no risk of a build-time /
query-time embedding-function mismatch.

FAISS (`faiss-cpu`) + `sentence-transformers` avoids `onnxruntime` entirely
(unlike a Chroma-backed store), which sidesteps the Windows
torch-vs-onnxruntime DLL load-order issue by construction rather than by
import ordering.
"""

from functools import lru_cache

from langchain_community.embeddings import HuggingFaceEmbeddings

from config.settings import EMBEDDING_MODEL_NAME


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """Return the shared `HuggingFaceEmbeddings` instance (loaded once)."""
    return HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL_NAME)
