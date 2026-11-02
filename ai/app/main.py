"""HTTP layer of the local ASR service.

Exposes the same JSON contract as the HF Space. By default the heavy
transcription runs on the Space (space_asr.prefer), with the local
engine as fallback; judging always stays local. Heavy imports happen
inside the route handlers, never at module import, so the server boots
fast and stays light until the first real request.
"""
from __future__ import annotations

import asyncio          # to_thread: transcription runs off the event loop
import base64
import binascii         # to catch bad base64
import tempfile
from pathlib import Path

import uvicorn          # to run the server

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import RedirectResponse

from .config import SERVER_HOST, SERVER_PORT

app = FastAPI(
    title="Tasmia ASR service",
    description="Recitation transcriber and judge. HF Space ASR by default, local fallback.",
    version="1.0.0",
)


@app.get("/")
def root():
    """Redirect the browser to the interactive API docs."""
    return RedirectResponse(url="/docs")


@app.get("/health")
def health():
    """Service heartbeat: which engines are loaded, on which device."""
    from .engine import ENGINES

    return {
        "status": "ok",
        "engines": ENGINES.snapshot(),
    }




@app.post("/api/transcribe")
async def transcribe(
    audio: UploadFile = File(...),
    model: str = Form(""),
    surah: int = Form(0),
    ayah_from: int = Form(1),
    ayah_to: int = Form(0),
    mode: str = Form(""),
):
    """Multipart route: a real file upload (browser form or Go backend).

    With surah=0 (default) this is a pure transcription. Give surah
    (plus optional ayah range and mode) and the response becomes a full
    judged session: text + per-word verdicts + score.
    """
    suffix = Path(audio.filename or "").suffix or ".wav"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(await audio.read())
        audio_path = handle.name

    try:
        from .asr import from_audio_to_text
        text = await asyncio.to_thread(from_audio_to_text, audio_path, model)
        response = {"text": text, "model": model or "quick"}

        if surah:
            check = _parse_mode(mode)
            from .pipeline import evaluate
            session = await asyncio.to_thread(
                evaluate, text, surah, ayah_from, ayah_to or None, check, model
            )
            response.update(session)
        return response

    except HTTPException:
        raise
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(audio_path).unlink(missing_ok=True)

    

@app.post("/api/transcribe/json")
async def transcribe_json(payload: dict):
    """JSON route: {"audio": "<base64 file bytes>", "model": "quick", "surah": 94, ...}.

    Same judging block as /api/transcribe when "surah" is present.
    """
    try:
        data = base64.b64decode(payload["audio"])
    except (KeyError, binascii.Error):
        raise HTTPException(status_code=400, detail="missing or invalid base64 'audio'")

    suffix = Path(payload.get("filename") or "").suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as handle:
        handle.write(data)
        audio_path = handle.name

    try:
        from .asr import from_audio_to_text
        model = str(payload.get("model") or "")
        text = await asyncio.to_thread(from_audio_to_text, audio_path, model)
        response = {"text": text, "model": model or "quick"}

        surah = int(payload.get("surah") or 0)
        if surah:
            check = _parse_mode(str(payload.get("mode") or ""))
            from .pipeline import evaluate
            session = await asyncio.to_thread(
                evaluate,
                text,
                surah,
                int(payload.get("ayah_from") or 1),
                int(payload.get("ayah_to") or 0) or None,
                check,
                model,
            )
            response.update(session)
        return response

    except HTTPException:
        raise
    except NotImplementedError as exc:
        raise HTTPException(status_code=501, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
    finally:
        Path(audio_path).unlink(missing_ok=True)


def _parse_mode(mode: str):
    """Translate a client mode string into the core enum (bad value -> 400)."""
    from tasmia_core.models import kinds_checks

    if not mode:
        return kinds_checks.without_tashkeel
    try:
        return kinds_checks(mode)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"unknown mode '{mode}'")


def main() -> None:
    """Run the service on the address from config.json (server_web)."""
    uvicorn.run(app, host=SERVER_HOST, port=SERVER_PORT)


if __name__ == "__main__":
    main()