"""LangChain vectorstore - FAISS index over `embedding/` knowledge-base docs.

Used by `langchain_app.tools.retrieval_tool` as the retriever behind the
agent's RAG tool. FAISS is used in-process (no external vector DB service),
per the plan's "Vector store" architecture decision.

Rebuild strategy is deliberately simple: the whole `embedding/` directory
is a handful of small markdown files, so `get_vectorstore()` just loads the
persisted index if one exists on disk, or rebuilds it from scratch
otherwise (`force_rebuild=True` to always rebuild, e.g. after editing
`embedding/` docs). This skips the per-file hash/manifest incremental-sync
machinery the earlier Chroma-based prototype needed - not worth the
complexity for a knowledge base this size.
"""

import hashlib
import re
from functools import lru_cache
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document

from config.settings import VECTOR_STORE_DIR
from langchain_app.vectorstore.embeddings import get_embeddings

_EMBEDDING_DIR = Path(__file__).resolve().parents[2] / "embedding"
_INDEX_DIR = Path(VECTOR_STORE_DIR)
_SUPPORTED_EXTENSIONS = {".md", ".txt", ".sql"}
_SOURCE_HASH_FILE_NAME = "source_hash.txt"

_HEADER_SPLIT_RE = re.compile(r"\n(?=##?\s+)")


def _chunk_markdown(content: str, source: str) -> list[Document]:
    """Split markdown by level-1/level-2 headers into retrievable chunks."""
    documents = []
    for section in _HEADER_SPLIT_RE.split(content):
        cleaned = section.strip()
        if not cleaned:
            continue
        title = cleaned.splitlines()[0].strip("# ").strip()
        documents.append(Document(page_content=cleaned, metadata={"source": source, "title": title}))
    return documents


def load_documents() -> list[Document]:
    """Read every supported file under `embedding/` and chunk it by header.

    `README.md` is folder meta-documentation, not knowledge-base content,
    so it's excluded even though it matches the `.md` extension.
    """
    if not _EMBEDDING_DIR.exists():
        return []

    documents = []
    for file_path in sorted(_EMBEDDING_DIR.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            continue
        if file_path.name.lower() == "readme.md":
            continue
        rel_path = str(file_path.relative_to(_EMBEDDING_DIR))
        content = file_path.read_text(encoding="utf-8")
        documents.extend(_chunk_markdown(content, rel_path))
    return documents


def _source_hash() -> str:
    """Hash of every indexed `embedding/` doc's content, to detect when a
    persisted index is stale relative to the current source docs (e.g.
    after editing db_diagrams.md/sample_sqls.md) without needing an
    explicit force_rebuild=True."""
    digest = hashlib.sha256()
    for file_path in sorted(_EMBEDDING_DIR.rglob("*")):
        if not file_path.is_file() or file_path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
            continue
        if file_path.name.lower() == "readme.md":
            continue
        digest.update(file_path.read_bytes())
    return digest.hexdigest()


def build_index() -> FAISS:
    """Build the FAISS index from `embedding/` docs and persist it to disk,
    alongside a hash of the source content so staleness can be detected
    automatically on the next load."""
    documents = load_documents()
    if not documents:
        raise RuntimeError(
            f"No documents found under {_EMBEDDING_DIR} - nothing to index."
        )
    vectorstore = FAISS.from_documents(documents, get_embeddings())
    _INDEX_DIR.mkdir(parents=True, exist_ok=True)
    vectorstore.save_local(str(_INDEX_DIR))
    (_INDEX_DIR / _SOURCE_HASH_FILE_NAME).write_text(_source_hash(), encoding="utf-8")
    return vectorstore


def _index_is_stale() -> bool:
    hash_path = _INDEX_DIR / _SOURCE_HASH_FILE_NAME
    if not hash_path.exists():
        return True  # index built before hash-tracking existed, or hash file removed
    return hash_path.read_text(encoding="utf-8").strip() != _source_hash()


def _load_persisted_index() -> FAISS | None:
    if not (_INDEX_DIR / "index.faiss").exists() or _index_is_stale():
        return None
    return FAISS.load_local(
        str(_INDEX_DIR), get_embeddings(), allow_dangerous_deserialization=True
    )


@lru_cache(maxsize=1)
def _cached_vectorstore() -> FAISS:
    return _load_persisted_index() or build_index()


def get_vectorstore(force_rebuild: bool = False) -> FAISS:
    """Return the FAISS vectorstore, loading from disk or building it."""
    if force_rebuild:
        build_index()
        _cached_vectorstore.cache_clear()
    return _cached_vectorstore()


def get_retriever(k: int = 3, force_rebuild: bool = False):
    """Return a retriever over the FAISS vectorstore for `retrieval_tool`."""
    return get_vectorstore(force_rebuild=force_rebuild).as_retriever(search_kwargs={"k": k})
