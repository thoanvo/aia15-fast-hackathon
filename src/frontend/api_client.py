"""Frontend - Backend API Client.

Thin HTTP wrapper around the backend's REST API
(backend.controllers.chat_controller), used by frontend.pages.chat and
frontend.pages.home. Deliberately does not import anything from
`config.settings` - the frontend never talks to the DB or the LLM gateway
directly, only to the backend over HTTP, so it shouldn't need those secrets.
"""

import os
from pathlib import Path

import requests
from dotenv import load_dotenv

load_dotenv(dotenv_path=Path(__file__).resolve().parent.parent.parent / ".env")

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000").rstrip("/")
_TIMEOUT_SECONDS = 60
_HEALTH_TIMEOUT_SECONDS = 5

# The backend is always local/intranet, so it should never go through a
# corporate web-filtering proxy - even if one is configured system-wide via
# HTTP_PROXY/HTTPS_PROXY (some corporate proxies block loopback traffic
# outright, which would otherwise break every call below).
_session = requests.Session()
_session.trust_env = False


def send_message(conversation_id: str, question: str) -> tuple[str, list[str], list[str], list[dict] | None]:
    """POST /api/v1/chat -> (answer text, DB tables the answer was sourced from,
    KB chunks used, chart-ready records or None if nothing chart-worthy)."""
    response = _session.post(
        f"{BACKEND_URL}/api/v1/chat",
        json={"conversation_id": conversation_id, "question": question},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    return data["answer"], data.get("source_tables", []), data.get("kb_chunks", []), data.get("chart_data")


def get_history(conversation_id: str) -> list[dict]:
    """GET /api/v1/chat/{id}/history -> list of {role, content} messages."""
    response = _session.get(
        f"{BACKEND_URL}/api/v1/chat/{conversation_id}/history", timeout=_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()["messages"]


def generate_insight(conversation_id: str, question: str) -> str:
    """POST /api/v1/chat/{id}/insight -> generated insight text."""
    response = _session.post(
        f"{BACKEND_URL}/api/v1/chat/{conversation_id}/insight",
        json={"question": question},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["insight"]


def generate_recommendation(conversation_id: str, insight: str) -> str:
    """POST /api/v1/chat/{id}/recommendation -> generated recommendation text."""
    response = _session.post(
        f"{BACKEND_URL}/api/v1/chat/{conversation_id}/recommendation",
        json={"insight": insight},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["recommendation"]


def clear_conversation(conversation_id: str) -> None:
    """DELETE /api/v1/chat/{id} - clear a conversation's history."""
    response = _session.delete(f"{BACKEND_URL}/api/v1/chat/{conversation_id}", timeout=_TIMEOUT_SECONDS)
    response.raise_for_status()


def check_backend_health() -> bool:
    """GET /health - is the backend process up?"""
    try:
        response = _session.get(f"{BACKEND_URL}/health", timeout=_HEALTH_TIMEOUT_SECONDS)
        return response.status_code == 200
    except requests.RequestException:
        return False


def check_db_health() -> bool:
    """GET /health/db - is the backend's database connection up?"""
    try:
        response = _session.get(f"{BACKEND_URL}/health/db", timeout=_HEALTH_TIMEOUT_SECONDS)
        return response.status_code == 200
    except requests.RequestException:
        return False


def check_rag_health() -> dict:
    """GET /health/rag -> {"status": ..., "total_chunks": ...}. Never raises."""
    try:
        response = _session.get(f"{BACKEND_URL}/health/rag", timeout=_HEALTH_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
        return {"status": "unavailable"}
    except requests.RequestException:
        return {"status": "unavailable"}


def get_fixed_tools_enabled() -> bool:
    """GET /api/v1/settings/fixed-tools-enabled -> current FIXED_TOOLS_ENABLED state."""
    response = _session.get(
        f"{BACKEND_URL}/api/v1/settings/fixed-tools-enabled", timeout=_HEALTH_TIMEOUT_SECONDS
    )
    response.raise_for_status()
    return response.json()["fixed_tools_enabled"]


def set_fixed_tools_enabled(enabled: bool) -> bool:
    """PUT /api/v1/settings/fixed-tools-enabled -> the resulting state, for the demo toggle."""
    response = _session.put(
        f"{BACKEND_URL}/api/v1/settings/fixed-tools-enabled",
        json={"fixed_tools_enabled": enabled},
        timeout=_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    return response.json()["fixed_tools_enabled"]


def check_tts_health() -> dict:
    """GET /api/v1/tts/status -> {"available": bool, "downloading": bool, "model": str}. Never raises."""
    try:
        response = _session.get(f"{BACKEND_URL}/api/v1/tts/status", timeout=_HEALTH_TIMEOUT_SECONDS)
        if response.status_code == 200:
            return response.json()
        return {"available": False, "downloading": False}
    except requests.RequestException:
        return {"available": False, "downloading": False}


def synthesize_speech(text: str, voice: str = "af_bella", speed: float = 1.0) -> bytes | None:
    """POST /api/v1/tts -> raw WAV bytes, or None on failure.

    Returns None (rather than raising) so callers can show a graceful error
    instead of crashing the Streamlit page.
    """
    try:
        response = _session.post(
            f"{BACKEND_URL}/api/v1/tts",
            json={"text": text, "voice": voice, "speed": speed},
            timeout=130,  # CPU synthesis of a long answer can take ~1-2 minutes; stay above the backend's 120s budget
        )
        if response.status_code == 200:
            return response.content
        return None
    except requests.RequestException:
        return None
