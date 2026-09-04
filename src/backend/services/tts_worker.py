"""Standalone entry point for isolated Kokoro TTS synthesis.

Run as `python -m backend.services.tts_worker` with a JSON request on stdin:
    {"text": ..., "voice": ..., "speed": ..., "onnx_path": ..., "voices_path": ...}

Writes raw WAV bytes to stdout on success. On failure, writes the error
message to stderr and exits non-zero.

This must be a real subprocess (`subprocess.Popen`), not a
`multiprocessing.Process` — Windows' spawn start method re-imports whatever
module launched the parent, which on this project would re-run heavy,
possibly slow/network-touching imports (see e.g. dev_fake_backend.py's
unguarded top-level imports). Isolation also means a hung call can be killed
outright by the caller (tts_service.py), which a stuck thread cannot be.
"""

import io
import json
import sys

# onnxruntime's compiled extension (onnxruntime_pybind11_state) fails to
# load standalone on this machine ("DLL load failed") unless torch has
# already registered its bundled runtime DLLs earlier in the same process —
# torch's own native init satisfies a dependency onnxruntime otherwise can't
# find (normally covered by installing the VC++ redistributable). Importing
# torch first, purely for that side effect, is what let this work at all in
# the original single-process design (the RAG stack always loads torch
# before any TTS call).
import torch  # noqa: F401


def main() -> None:
    request = json.loads(sys.stdin.read())

    from kokoro_onnx import Kokoro
    import soundfile as sf

    kokoro = Kokoro(request["onnx_path"], request["voices_path"])
    samples, sample_rate = kokoro.create(
        request["text"], voice=request["voice"], speed=request["speed"], lang="en-us"
    )
    buf = io.BytesIO()
    sf.write(buf, samples, sample_rate, format="WAV")
    sys.stdout.buffer.write(buf.getvalue())
    sys.stdout.buffer.flush()


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:  # noqa: BLE001
        sys.stderr.write(str(exc))
        sys.exit(1)