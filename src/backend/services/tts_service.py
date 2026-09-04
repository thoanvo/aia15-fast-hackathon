"""Backend Service - Text-to-Speech (TTS).

Uses kokoro-onnx (Kokoro-82M v1.0, ONNX runtime) for high-quality, CPU-only TTS.
Model files are stored in src/tts_models/ and downloaded automatically at
backend startup if not yet present (non-blocking background thread).

Model files (~114 MB total):
  - kokoro-v1.0.int8.onnx  (~88 MB)  — quantized acoustic model (fastest on CPU)
  - voices-v1.0.bin         (~26 MB)  — voice embeddings

Source: https://github.com/thewh1teagle/kokoro-onnx/releases/tag/model-files-v1.0
"""

import json
import logging
import re
import subprocess
import sys
import threading
from pathlib import Path

import requests as _requests  # use requests (not urllib) to bypass SSL cert issues

logger = logging.getLogger(__name__)

# Synthesis runs in a dedicated `tts_worker.py` subprocess (plain
# `subprocess.Popen`, not `multiprocessing.Process` — Windows' spawn start
# method re-imports whatever module launched the parent, which on this
# project can mean re-running slow/network-touching imports). Isolation also
# means a hung call can be killed outright on timeout, unlike a stuck thread
# which can only be abandoned. See tts_worker.py for why it imports torch
# before onnxruntime.
#
# CPU-only inference for a realistic multi-sentence answer (a few hundred
# characters) measured at ~45s, so 30s was cutting off legitimate synthesis,
# not just runaway calls — this needs to stay generous. Keep the frontend's
# request timeout (src/frontend/api_client.py, synthesize_speech) above this.
_SYNTHESIS_TIMEOUT_SECONDS = 120
_SRC_DIR = Path(__file__).resolve().parent.parent.parent

# Assistant replies are Markdown. Left in, espeak-ng phonemizes the raw
# symbols (list markers, emphasis, links) instead of prose, which is what
# triggers phonemizer's "words count mismatch" warning.
_MD_LINK_RE = re.compile(r"\[([^\]]*)\]\([^)]*\)")
_MD_TABLE_ROW_RE = re.compile(r"^\s*\|?[\s:|-]+\|?\s*$", re.MULTILINE)
_MD_HEADER_RE = re.compile(r"^#{1,6}\s+", re.MULTILINE)
_MD_LIST_MARKER_RE = re.compile(r"^\s*(?:[-*+]|\d+[.)])\s+", re.MULTILINE)
_MD_EMPHASIS_RE = re.compile(r"(\*\*\*|\*\*|\*|___|__|_|`{1,3})")


def _strip_markdown(text: str) -> str:
    """Strip Markdown so espeak phonemizes prose, not literal symbols."""
    text = _MD_LINK_RE.sub(r"\1", text)
    text = _MD_TABLE_ROW_RE.sub("", text)
    text = _MD_HEADER_RE.sub("", text)
    text = _MD_LIST_MARKER_RE.sub("", text)
    text = _MD_EMPHASIS_RE.sub("", text)
    return text

# Model files live alongside src/ so they persist across restarts.
TTS_MODEL_DIR = _SRC_DIR / "tts_models"
TTS_ONNX_PATH  = TTS_MODEL_DIR / "kokoro-v1.0.int8.onnx"
TTS_VOICES_PATH = TTS_MODEL_DIR / "voices-v1.0.bin"

_BASE_URL = (
    "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0"
)
_ONNX_URL   = f"{_BASE_URL}/kokoro-v1.0.int8.onnx"
_VOICES_URL = f"{_BASE_URL}/voices-v1.0.bin"

# Tracks whether a background download is currently in progress.
_downloading = False


def is_model_available() -> bool:
    """Return True if both model files are present on disk."""
    return TTS_ONNX_PATH.exists() and TTS_VOICES_PATH.exists()


def is_downloading() -> bool:
    """Return True while a background model download is in progress."""
    return _downloading


def _download_file(url: str, dest: Path, label: str) -> None:
    """Stream *url* to *dest* using requests (SSL verify=False for corp proxies)."""
    logger.info("TTS: downloading %s ...", label)
    tmp = dest.with_suffix(".tmp")
    try:
        with _requests.get(url, stream=True, verify=False, timeout=30,
                           allow_redirects=True) as resp:
            resp.raise_for_status()
            total = int(resp.headers.get("content-length", 0))
            downloaded = 0
            with open(tmp, "wb") as f:
                for chunk in resp.iter_content(chunk_size=1024 * 1024):
                    if chunk:
                        f.write(chunk)
                        downloaded += len(chunk)
                        if total and downloaded % (10 * 1024 * 1024) < 1024 * 1024:
                            pct = downloaded / total * 100
                            logger.info("TTS: %s — %.0f%% (%.0f MB)", label, pct, downloaded / 1e6)
        tmp.rename(dest)
        logger.info("TTS: %s saved to %s", label, dest.name)
    except Exception:
        tmp.unlink(missing_ok=True)
        raise


def download_models() -> None:
    """Download model files synchronously (runs in a background thread)."""
    global _downloading
    TTS_MODEL_DIR.mkdir(parents=True, exist_ok=True)
    try:
        if not TTS_ONNX_PATH.exists():
            _download_file(_ONNX_URL, TTS_ONNX_PATH, "kokoro-v1.0.int8.onnx")
        if not TTS_VOICES_PATH.exists():
            _download_file(_VOICES_URL, TTS_VOICES_PATH, "voices-v1.0.bin")
        logger.info("TTS: all model files ready in %s", TTS_MODEL_DIR)
    except Exception:
        logger.exception("TTS: model download failed — TTS will be unavailable until the next restart")
    finally:
        _downloading = False


def ensure_models_async() -> None:
    """Trigger a background download if model files are missing.

    Called once at app startup. Returns immediately so the server is available
    straight away even while models are being fetched.
    """
    global _downloading
    if is_model_available():
        logger.info("TTS: model files already present — skipping download.")
        return
    logger.info(
        "TTS: model files not found — starting background download (~114 MB). "
        "Server is available now; TTS will work once the download finishes."
    )
    _downloading = True
    thread = threading.Thread(target=download_models, daemon=True, name="tts-model-download")
    thread.start()


def synthesize(text: str, voice: str = "af_bella", speed: float = 1.0) -> bytes:
    """Synthesize *text* and return raw WAV bytes.

    Args:
        text:  The text to speak.
        voice: Kokoro voice ID (default: af_bella — American English, female).
        speed: Speech speed multiplier (0.5–2.0; 1.0 = normal).

    Raises:
        RuntimeError: If model files are not available, or synthesis times out.
    """
    if not is_model_available():
        if _downloading:
            raise RuntimeError(
                "TTS model is still downloading (~114 MB). Please wait a moment and try again."
            )
        raise RuntimeError(
            "TTS model files are not available. Restart the server to trigger a download."
        )

    text = _strip_markdown(text).strip()
    if not text:
        raise RuntimeError("Nothing to synthesize after removing Markdown formatting.")

    request = json.dumps({
        "text": text,
        "voice": voice,
        "speed": speed,
        "onnx_path": str(TTS_ONNX_PATH),
        "voices_path": str(TTS_VOICES_PATH),
    })
    logger.info("TTS: synthesizing in an isolated process ...")
    process = subprocess.Popen(
        [sys.executable, "-m", "backend.services.tts_worker"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=str(_SRC_DIR),
    )
    try:
        wav_bytes, stderr = process.communicate(
            input=request.encode("utf-8"), timeout=_SYNTHESIS_TIMEOUT_SECONDS
        )
    except subprocess.TimeoutExpired:
        process.kill()
        process.communicate()
        raise RuntimeError(f"TTS synthesis timed out after {_SYNTHESIS_TIMEOUT_SECONDS}s.")

    if process.returncode != 0:
        raise Exception(  # noqa: TRY002
            f"TTS synthesis failed: {stderr.decode(errors='replace').strip()}"
        )

    logger.info("TTS: synthesis complete.")
    return wav_bytes
