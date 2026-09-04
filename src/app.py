"""FastAPI composition root.

Run from src/:
    uvicorn app:app --reload
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException

from backend.controllers.chat_controller import router as chat_router
from backend.controllers.settings_controller import router as settings_router
from backend.controllers.tts_controller import router as tts_router
from backend.services import tts_service
from config.settings import (
    EMBEDDING_MODEL_NAME,
    OOS_ENABLED,
    OOS_SIMILARITY_THRESHOLD,
    OPENAI_BASE_URL,
    OPENAI_MODEL,
    OPENAI_VERIFY_SSL,
    VECTOR_STORE_DIR,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Run startup tasks before the server starts accepting requests."""
    # Kick off TTS model download in the background if model files are missing.
    # This never blocks the server — it logs progress and finishes silently.
    tts_service.ensure_models_async()
    yield


app = FastAPI(
    title="Database Query Assistant API",
    version="1.0.0",
    description=(
        "LangChain agent (business tools + RAG retrieval) backend for the "
        "Database Query Assistant (see docs/01_business_requirements.md)."
    ),
    lifespan=lifespan,
)

app.include_router(chat_router, prefix="/api/v1")
app.include_router(settings_router, prefix="/api/v1")
app.include_router(tts_router, prefix="/api/v1")

# Log the resolved (non-secret) config once at startup - never guess whether
# a .env change actually took effect from a stack trace again. In
# particular, OPENAI_VERIFY_SSL is the single most common cause of
# `SSL: CERTIFICATE_VERIFY_FAILED` (see docs/09_environment_setup_guide.md
# Troubleshooting C) - if it's not printing what you just set in `.env`,
# either the file isn't at the repo root, the line has a typo, or the
# process wasn't restarted after editing it.
logger.info(
    "Config: OPENAI_MODEL=%s OPENAI_BASE_URL=%s OPENAI_VERIFY_SSL=%s "
    "EMBEDDING_MODEL_NAME=%s VECTOR_STORE_DIR=%s OOS_ENABLED=%s "
    "OOS_SIMILARITY_THRESHOLD=%s",
    OPENAI_MODEL,
    OPENAI_BASE_URL,
    OPENAI_VERIFY_SSL,
    EMBEDDING_MODEL_NAME,
    VECTOR_STORE_DIR,
    OOS_ENABLED,
    OOS_SIMILARITY_THRESHOLD,
)


@app.get("/health", tags=["health"])
def health() -> dict:
    """Basic liveness check."""
    return {"status": "ok"}


@app.get("/health/db", tags=["health"])
def health_db() -> dict:
    """Verify the configured PostgreSQL (Neon) database is reachable."""
    from database.connection.connection_pool import check_connection

    try:
        check_connection()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"Database unreachable: {exc}") from exc
    return {"status": "ok"}


@app.get("/health/rag", tags=["health"])
def health_rag() -> dict:
    """Report the FAISS RAG vector store status (loads/builds it on first call)."""
    from langchain_app.vectorstore.store import get_vectorstore

    try:
        vectorstore = get_vectorstore()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=503, detail=f"RAG vector store unavailable: {exc}") from exc
    return {"status": "ready", "total_chunks": vectorstore.index.ntotal}
