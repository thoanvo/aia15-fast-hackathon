"""Controller Layer - TTS Controller.

Exposes two endpoints:
  POST /api/v1/tts          — synthesise text and return WAV audio bytes.
  GET  /api/v1/tts/status   — report model availability (used by sidebar).
"""

import logging

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field

from backend.services import tts_service

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/tts", tags=["tts"])


class TTSRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesise.")
    voice: str = Field(default="af_bella", description="Kokoro voice ID.")
    speed: float = Field(default=1.0, ge=0.5, le=2.0, description="Speech speed (0.5–2.0).")


@router.post("", summary="Synthesise text to WAV audio")
def post_tts(request: TTSRequest) -> Response:
    """Convert *text* to speech and return raw WAV bytes (audio/wav).

    Returns HTTP 503 while the model is still downloading so the frontend
    can show a friendly 'try again shortly' message instead of a hard error.
    """
    try:
        wav_bytes = tts_service.synthesize(request.text, voice=request.voice, speed=request.speed)
    except RuntimeError as exc:
        # Model downloading or unavailable — tell the client to retry.
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except Exception as exc:  # noqa: BLE001
        logger.exception("TTS synthesis failed")
        raise HTTPException(status_code=500, detail="TTS synthesis failed.") from exc
    return Response(content=wav_bytes, media_type="audio/wav")


@router.get("/status", summary="TTS model availability status")
def get_tts_status() -> dict:
    """Report whether the TTS model is ready to serve requests."""
    return {
        "available": tts_service.is_model_available(),
        "downloading": tts_service.is_downloading(),
        "model": "kokoro-v1.0.int8",
    }
