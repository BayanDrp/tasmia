"""ASR step: an audio file goes in, raw transcript text comes out.

Thin orchestration only. The sound domain lives in audio.py, the model
domain in engine.py; this file never loads weights and never decodes
media itself.
"""

from __future__ import annotations

from tasmia_core.normalize import collapse_repetition, merge_chunk_texts

from .audio import decode_audio, is_silent, split_audio
from .engine import ENGINES, resolve_model, transcribe_chunk


def from_audio_to_text(audio_path: str, model_key: str = "", language: str = "ar") -> str:
    """Transcribe one audio file to text with the selected engine.

    model_key accepts an alias from config.json ('quick'/'warsh') or
    any Hugging Face ASR repo id.
    """
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
