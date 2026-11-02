

from __future__ import annotations

import os

os.environ["GRADIO_SSR_MODE"] = "False"  # must precede gradio import; override runner

import tempfile  # noqa: E402
import threading  # noqa: E402
import time  # noqa: E402

import gradio as gr  # noqa: E402
import spaces  # noqa: E402
from config import DEFAULT_MODEL_ALIAS, MAX_AUDIO_SECONDS  # noqa: E402
from fastapi import File, Form, UploadFile  # noqa: E402
from fastapi.responses import JSONResponse, RedirectResponse  # noqa: E402
from gradio import Server  # noqa: E402
from starlette.concurrency import run_in_threadpool  # noqa: E402

GPU_DURATION_SECONDS = 120  # cold >3 GB loads may still exceed; retried calls hit cache


@spaces.GPU(duration=GPU_DURATION_SECONDS)
def run_transcribe(audio_path: str, model_key: str, language: str = "ar") -> dict:
    """One end to end transcription; the model stays on GPU between calls."""
    from engine import resolve_model, transcribe_transcript  # lazy: heavy imports

    started = time.perf_counter()
    model_id = resolve_model(model_key)
    kind, text, chunks, audio_seconds = transcribe_transcript(audio_path, model_id, language)

    return {
        "transcription": text,
        "model": model_id,
        "type": kind,
        "elapsed_ms": int((time.perf_counter() - started) * 1000),
        "chunks": chunks,
        "audio_seconds": audio_seconds,
    }


def _transcribe_sync(payload: bytes, suffix: str, model: str, language: str) -> dict:
    """Shared body of every endpoint: bytes in, result dict out."""
    fd, incoming_path = tempfile.mkstemp(suffix=suffix)
    try:
        with os.fdopen(fd, "wb") as incoming:
            incoming.write(payload)
        return run_transcribe(incoming_path, model, language)
    finally:
        try:
            os.unlink(incoming_path)
        except OSError:
            pass


# --------------------------------------------------------------------------
# JSON API
# --------------------------------------------------------------------------

app = Server(title="Tasmia API", version="1.0")


@app.post("/api/transcribe")
async def api_transcribe_multipart(
    audio: UploadFile = File(...),
    model: str = Form(DEFAULT_MODEL_ALIAS),
    language: str = Form("ar"),
    surah: int = Form(0),
    ayah_from: int = Form(1),
    ayah_to: int = Form(0),
    mode: str = Form(""),
):
    payload = await audio.read()
    if not payload:
        return JSONResponse(status_code=400, content={"error": "audio file is empty"})

    suffix = os.path.splitext(audio.filename or "clip.wav")[1] or ".wav"
    return await _transcribe_payload(
        payload, suffix, model, language, surah, ayah_from, ayah_to, mode
    )


@app.post("/api/transcribe/json")
async def api_transcribe_json(request_data: dict):
    """Machine to machine variant (JSON body, base64 audio)."""
    audio_b64 = request_data.get("audio_base64")
    model = request_data.get("model", DEFAULT_MODEL_ALIAS)
    language = request_data.get("language", "ar")

    if not audio_b64:
        return JSONResponse(status_code=400, content={"error": "audio_base64 is required"})

    import base64
    import binascii

    try:
        payload = base64.b64decode(audio_b64, validate=True)
    except (binascii.Error, ValueError):
        return JSONResponse(status_code=400, content={"error": "audio_base64 is not valid base64"})

    if not payload:
        return JSONResponse(status_code=400, content={"error": "audio file is empty"})

    try:
        surah = int(request_data.get("surah") or 0)
        ayah_from = int(request_data.get("ayah_from") or 1)
        ayah_to = int(request_data.get("ayah_to") or 0)
        mode = str(request_data.get("mode") or "")
    except (TypeError, ValueError):
        return JSONResponse(
            status_code=400,
            content={"error": "invalid surah, ayah_from, or ayah_to"},
        )

    name = str(request_data.get("filename") or "clip.wav")
    return await _transcribe_payload(
        payload,
        os.path.splitext(name)[1] or ".wav",
        model,
        language,
        surah,
        ayah_from,
        ayah_to,
        mode,
    )


async def _transcribe_payload(
    payload: bytes,
    suffix: str,
    model: str,
    language: str,
    surah: int = 0,
    ayah_from: int = 1,
    ayah_to: int = 0,
    mode: str = "",
):
    try:
        started = time.perf_counter()
        result = await run_in_threadpool(
            _transcribe_sync,
            payload,
            suffix,
            (model or "").strip() or DEFAULT_MODEL_ALIAS,
            language,
        )
        result = dict(result)
        result.setdefault("text", str(result.get("transcription", "")).strip())
        if not surah:
            return result

        from judge import evaluate, parse_mode

        session = await run_in_threadpool(
            evaluate,
            result["text"],
            surah,
            ayah_from,
            ayah_to or None,
            parse_mode(mode),
            str(result.get("model", "")),
            int((time.perf_counter() - started) * 1000),
        )
        response = {"text": result["text"], "model": result.get("model", "")}
        response.update(session)
        return response
    except ValueError as exc:
        return JSONResponse(status_code=400, content={"error": str(exc)})
    except Exception as exc:  # keep strangers from getting full tracebacks
        return JSONResponse(status_code=400, content={"error": f"processing failed: {exc}"})


@app.api(name="transcribe")
def _api_queue_transcribe(audio_base64: str, model: str = "") -> dict:
    """Queue/SSE fallback: POST /gradio_api/call/transcribe {"data": [b64, model]}.

    This path goes through gradio's own queue (proven to work even when the
    Node SSR proxy is fronting the app).
    """
    import base64
    import binascii

    try:
        payload = base64.b64decode(audio_base64 or "", validate=True)
    except (binascii.Error, ValueError) as exc:
        raise ValueError("audio_base64 is not valid base64") from exc
    if not payload:
        raise ValueError("audio_base64 decodes to empty bytes")
    return _transcribe_sync(payload, ".wav", (model or "").strip() or DEFAULT_MODEL_ALIAS, "ar")


@app.get("/whoami", include_in_schema=False)
async def whoami():
    from engine import ENGINES, ENGINE_ALIASES  # lazy

    return {
        "service": "tasmia",
        # contract 2 = edge trim + collapse_repetition present; the local
        # fallback checks this before trusting Space transcripts
        "contract": 2,
        "features": {"trim_silence": True, "collapse_repetition": True},
        "aliases": ENGINE_ALIASES,
        "loaded_engines": ENGINES.snapshot(),
    }


@app.get("/", include_in_schema=False)
async def redirect_home():
    return RedirectResponse(url="/gradio")


# --------------------------------------------------------------------------
# Demo UI - built in a function on purpose: a module-level Blocks would be
# auto launched by the HF runner instead of the Server (see module docstring).
# --------------------------------------------------------------------------

def _ui_transcribe(audio_path, model_key):
    if not audio_path:
        raise gr.Error("ارفع ملفًا صوتيًا أولًا.")
    key = (model_key or "").strip() or DEFAULT_MODEL_ALIAS
    try:
        result = run_transcribe(audio_path, key, "ar")
        return str(result.get("transcription", ""))
    except ValueError as exc:
        raise gr.Error(str(exc))
    except Exception as exc:  # noqa: BLE001
        raise gr.Error(f"تعذر تفريغ التسجيل: {exc}")


def _build_demo() -> gr.Blocks:
    with gr.Blocks(title="Tasmia | Warsh ASR") as demo:
        gr.Markdown(
            "# تَسْمِيَة\n"
            "تفريغ التلاوة القرآنية إلى نص عربي عبر أي نموذج ASR. "
            "الافتراضي `rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final`؛ "
            "وبطاقة النموذج لا تؤكد أنه مخصص لرواية ورش."
        )
        audio_input = gr.Audio(
            sources=["upload", "microphone"],
            type="filepath",
            label="ارفع تسجيلًا أو سجّل تلاوتك",
        )
        model_box = gr.Textbox(
            label="النموذج (اختياري)",
            value="",
            placeholder="quick | warsh | أي مُعرِّف نموذج على Hugging Face",
            info="افتراضيًا quick؛ يمكن استدعاء أي نموذج ASR على HF بالمعرِّف الكامل.",
        )
        transcribe_button = gr.Button("تفريغ التلاوة", variant="primary")
        transcript = gr.Textbox(label="النص المتعرّف عليه", lines=7, rtl=True)
        gr.Markdown(
            "قد يخطئ التفريغ في الكلمات أو التشكيل؛ راجع النص على مصحف موثوق. "
            f"الحد الأقصى للتسجيل {MAX_AUDIO_SECONDS // 60} دقائق."
        )
        transcribe_button.click(_ui_transcribe, inputs=[audio_input, model_box], outputs=transcript)
    return demo


gr.mount_gradio_app(app, _build_demo(), path="/gradio")


# --------------------------------------------------------------------------
# Boot
# --------------------------------------------------------------------------

def _warm_default_engines():
    """Pre load the fast default engine on CPU at boot (outside GPU time)."""
    thread = threading.Thread(target=_safe_warm, args=(DEFAULT_MODEL_ALIAS,), daemon=True)
    thread.start()


def _safe_warm(model_key):
    try:
        from engine import ENGINES, resolve_model  # lazy: heavy imports

        ENGINES.get_or_load(resolve_model(model_key))
    except Exception as exc:  # a failed warm-up must never kill the boot
        print(f"[tasmia] warm-up failed for {model_key}: {exc}")


def _port_already_serving_our_app() -> bool:
    """True if another instance of THIS app already bound the port (the runner
    sometimes double starts; that must be benign, not RUNTIME_ERROR)."""
    import urllib.request

    port = os.getenv("GRADIO_SERVER_PORT", "7860")
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/whoami", timeout=5) as resp:
            return b'"service":"tasmia"' in resp.read()
    except Exception:
        return False


def _launch_with_retry():
    """Bind with retries: a stale server from the previous deployment can hold
    the port while the runner tears it down."""
    last_error: Exception | None = None
    for attempt in range(1, 13):
        try:
            app.launch(ssr_mode=False)
            return
        except OSError as exc:  # EADDRINUSE and friends
            last_error = exc
            if _port_already_serving_our_app():
                print("[tasmia] port already serving this app; parking duplicate process")
                while True:
                    time.sleep(3600)
            print(f"[tasmia] launch attempt {attempt} failed: {exc}; retrying in 10 s")
            time.sleep(10)
    raise last_error


_warm_default_engines()


if __name__ == "__main__":
    _launch_with_retry()
