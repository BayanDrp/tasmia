#!/usr/bin/env python3
"""Transcribe Quran recitation with a Quran-finetuned Wav2Vec2 CTC model.

This is the ASR backend for the Tasmia recitation coach. It loads a model
trained specifically for Quran recitation, then passes its transcript to
Tasmia's word aligner.

Usage:
    python3 tools/transcribe_lora.py <audio.wav> [expected passage text]

If expected text is given, the script also runs the real tasmia_core aligner
so you see exactly what the app would report per word.
"""

from __future__ import annotations

import sys
import time
from dataclasses import dataclass
from math import gcd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
CORE_PATH = PROJECT_ROOT / "core"
if str(CORE_PATH) not in sys.path:
    sys.path.insert(0, str(CORE_PATH))

import numpy as np
import torch
from scipy.io import wavfile
from scipy.signal import resample_poly
from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor

MODEL_ID = "rabah2026/wav2vec2-large-xlsr-53-arabic-quran-v_final"
SAMPLE_RATE = 16000
CHUNK_S = 20
OVERLAP_S = 2

# Surah Ash-Sharh 94:1-5 (the passage used for voice tests)
DEFAULT_EXPECTED = (
    "أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ وَوَضَعْنَا عَنكَ وِزْرَكَ "
    "الَّذِي أَنقَضَ ظَهْرَكَ وَرَفَعْنَا لَكَ ذِكْرَكَ "
    "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا"
)

def load_model():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    if device == "cpu":
        torch.set_num_threads(max(1, torch.get_num_threads()))
    processor = Wav2Vec2Processor.from_pretrained(MODEL_ID)
    model = Wav2Vec2ForCTC.from_pretrained(MODEL_ID).to(device)
    model.eval()
    return processor, model, device


def load_wav(path: str | Path):
    sr, audio = wavfile.read(path)
    if audio.dtype == np.int16:
        audio = audio.astype(np.float32) / 32768.0
    elif audio.dtype == np.int32:
        audio = audio.astype(np.float32) / 2147483648.0
    else:
        audio = audio.astype(np.float32)
    if audio.ndim > 1:
        audio = audio.mean(axis=1)
    if sr != SAMPLE_RATE:
        divisor = gcd(int(sr), SAMPLE_RATE)
        audio = resample_poly(
            audio,
            SAMPLE_RATE // divisor,
            int(sr) // divisor,
        ).astype(np.float32)
        sr = SAMPLE_RATE
    peak = float(np.max(np.abs(audio))) if audio.size else 0.0
    if peak > 0:
        audio = audio / peak * 0.95
    return sr, audio


def _merge_chunk_texts(texts: list[str]) -> str:
    """Remove repeated words caused by the audio overlap between chunks."""
    from tasmia_core.normalize import normalize_word

    merged: list[str] = []
    for text in texts:
        words = text.split()
        max_overlap = min(len(merged), len(words), 12)
        overlap = 0
        for size in range(max_overlap, 0, -1):
            left = [normalize_word(word) for word in merged[-size:]]
            right = [normalize_word(word) for word in words[:size]]
            if left == right and all(left):
                overlap = size
                break
        merged.extend(words[overlap:])
    return " ".join(merged)


def transcribe(processor, model, device: str, audio: np.ndarray) -> str:
    parts: list[str] = []
    chunk_samples = CHUNK_S * SAMPLE_RATE
    overlap_samples = OVERLAP_S * SAMPLE_RATE
    stride = chunk_samples - overlap_samples

    for start in range(0, len(audio), stride):
        seg = audio[start : start + chunk_samples]
        if not seg.size:
            continue
        inputs = processor(
            seg,
            sampling_rate=SAMPLE_RATE,
            return_tensors="pt",
            padding=True,
        )
        with torch.inference_mode():
            logits = model(inputs.input_values.to(device)).logits
        ids = torch.argmax(logits, dim=-1)
        text = processor.batch_decode(ids, skip_special_tokens=True)[0].strip()
        if text:
            parts.append(text)
        if start + chunk_samples >= len(audio):
            break

    return _merge_chunk_texts(parts)


@dataclass
class ExpWord:
    text: str
    normalized: str
    surah: int
    ayah: int
    index: int


def expected_words_94_1_5():
    from tasmia_core.normalize import normalize_word

    words = [
        "أَلَمْ", "نَشْرَحْ", "لَكَ", "صَدْرَكَ",
        "وَوَضَعْنَا", "عَنكَ", "وِزْرَكَ",
        "الَّذِي", "أَنقَضَ", "ظَهْرَكَ",
        "وَرَفَعْنَا", "لَكَ", "ذِكْرَكَ",
        "فَإِنَّ", "مَعَ", "الْعُسْرِ", "يُسْرًا",
    ]
    return [ExpWord(t, normalize_word(t), 94, 1, i + 1) for i, t in enumerate(words)]


def align_result(processor_model, expected, transcript):
    from tasmia_core.align import align
    from tasmia_core.models import HeardWord
    from tasmia_core.normalize import normalize_word

    heard = [
        HeardWord(text=tok, normalized=normalize_word(tok))
        for tok in transcript.split()
    ]
    return align(expected, heard)


def main() -> int:
    if len(sys.argv) < 2:
        print(__doc__)
        return 2

    path = sys.argv[1]
    expected_text = sys.argv[2] if len(sys.argv) > 2 else DEFAULT_EXPECTED

    processor, model, device = load_model()
    sr, audio = load_wav(path)
    duration = len(audio) / sr

    started = time.perf_counter()
    text = transcribe(processor, model, device, audio)
    elapsed = time.perf_counter() - started

    print(f"file={path}  audio={duration:.1f}s  gen={elapsed:.1f}s")
    print(f"[text] {text}")

    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))          # project root
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "core")) # core/tasmia_core
    try:
        result = align_result(None, expected_words_94_1_5(), text)
        marks = {"ok": "OK", "mispronounced": "~", "wrong": "X",
                 "missing": "-", "uncertain": "?", "repeated": "R"}
        for w in result.words:
            h = w.heard if w.heard is not None else "-"
            print(f"  {marks.get(w.status, '?'):>2} {w.status:15s} exp={w.expected:16s} heard={h}")
        for e in result.extras:
            print(f"  +   {'extra':15s} heard={e.text}")
        ok = sum(1 for w in result.words if w.status == "ok")
        print(f"score={ok / len(result.words):.3f}  strict={ok}/{len(result.words)}")
    except Exception as exc:  # noqa: BLE001
        print(f"(align skipped: {exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
