"""ASR step: an audio file goes in, raw transcript text comes out.

Thin orchestration only. The sound domain lives in audio.py, the model
domain in engine.py; this file never loads weights and never decodes
media itself.

The HF Space is the default ears when space_asr.enabled and
space_asr.prefer are true. If it fails, the local engine takes over.
Set prefer=false to keep the offline-first order (local first, Space
fallback). Judging always stays local: tasmia_core needs no torch.
"""

from __future__ import annotations

import base64
import json
import urllib.request
from pathlib import Path

from tasmia_core.normalize import collapse_repetition

from .config import SPACE_ASR_ENABLED, SPACE_ASR_PREFER, SPACE_ASR_TIMEOUT, SPACE_ASR_URL


def from_audio_to_text(audio_path: str, model_key: str = "", language: str = "ar") -> str:
    """Transcribe one audio file with the configured backend order.

    space_asr.enabled + space_asr.prefer:
        HF Space first, local engine as the fallback.
    space_asr.enabled + prefer=false:
        local engine first, HF Space as the fallback.
    space_asr.enabled=false:
        local engine only.

    model_key accepts an alias from config.json ('quick'/'warsh') or
    any Hugging Face ASR repo id.
    """
    if SPACE_ASR_ENABLED and SPACE_ASR_PREFER:
        return _space_then_local(audio_path, model_key, language)
    return _local_then_space(audio_path, model_key, language)


def _space_then_local(audio_path: str, model_key: str, language: str) -> str:
    """Default path: HF ears first, local engine if the Space fails."""
    try:
        return _space_transcription(audio_path, model_key, language)
    except Exception as space_error:
        try:
            return _local_transcription(audio_path, model_key, language)
        except Exception as local_error:
            # Both doors failed: report the local error, keep the chain.
            raise local_error from space_error


def _local_then_space(audio_path: str, model_key: str, language: str) -> str:
    """Offline-first path: local engine first, Space only as a fallback."""
    try:
        return _local_transcription(audio_path, model_key, language)
    except Exception as local_error:
        if not SPACE_ASR_ENABLED:
            raise
        try:
            return _space_transcription(audio_path, model_key, language)
        except Exception as space_error:
            # Both doors failed: report the local error, keep the chain.
            raise local_error from space_error


def _local_transcription(audio_path: str, model_key: str, language: str) -> str:
    """The local path: the torch engine."""
    # Lazy imports keep the HF-first path light: torch, numpy and
    # soundfile are only imported when the Space is unavailable.
    from .audio import decode_audio, is_silent, split_audio
    from .engine import ENGINES, resolve_model, transcribe_chunk
    from tasmia_core.normalize import merge_chunk_texts

    engine = ENGINES.get_or_load(resolve_model(model_key))

    audio, sample_rate = decode_audio(audio_path)

    texts = []
    for chunk in split_audio(audio, sample_rate):
        # Ignore near silent windows, which can trigger hallucinations.
        if is_silent(chunk):
            continue
        texts.append(transcribe_chunk(chunk, sample_rate, engine, language))

    text = merge_chunk_texts(texts)
    text = collapse_repetition(text)
    if not text:
        raise ValueError("لم أتمكن من تمييز كلام واضح في التسجيل.")

    return text


def _space_transcription(audio_path: str, model_key: str, language: str) -> str:
    """The HF path: the Space transcribes, we clean locally.

    Stdlib only (urllib), so this path adds no dependency and never
    imports torch. The Space answers {"transcription": ...}; the text is
    collapsed here too, so the guarantee holds even against an older
    Space.
    """
    audio_path = Path(audio_path)
    body = json.dumps({
        "audio_base64": base64.b64encode(audio_path.read_bytes()).decode("ascii"),
        "model": model_key,
        "language": language,
        "filename": audio_path.name,
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{SPACE_ASR_URL.rstrip('/')}/api/transcribe/json",
        data=body,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=SPACE_ASR_TIMEOUT) as response:
        answer = json.loads(response.read().decode("utf-8"))

    text = collapse_repetition(str(answer.get("transcription", "")).strip())
    if not text:
        raise ValueError("أعادت خدمة Hugging Face نصًا فارغًا.")
    return text
