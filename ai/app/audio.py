"""Sound domain: decode, trim and split recordings.

Works on raw samples only; it never sees a model. All values come from
the shared config.json (via ai/app/config.py).
"""

from __future__ import annotations

import subprocess
import tempfile

import numpy as np
import soundfile as sf

from .config import (
    CHUNK_OVERLAP_SECONDS,
    MAX_AUDIO_SECONDS,
    MAX_CHUNK_SECONDS,
    SILENCE_RMS,
    SAMPLE_RATE,
    TRIM_SILENCE,
)

TRIM_THRESHOLD_DB = -40  # silence level for the trim filter
TRIM_KEEP_SECONDS = 0.3  # keep this much real silence at each edge


def decode_audio(audio_path: str):
    """Decode common uploaded formats to mono 16 kHz float audio."""
    filters = ""
    if TRIM_SILENCE:
        # Trim silence at both edges: forward pass, reverse, forward, reverse.
        trim = (
            f"silenceremove=start_periods=1:start_threshold={TRIM_THRESHOLD_DB}dB"
            f":start_silence={TRIM_KEEP_SECONDS}"
        )
        filters = f"-af {trim},areverse,{trim},areverse"

    with tempfile.NamedTemporaryFile(suffix=".wav") as converted:
        command = [
            "ffmpeg",
            "-nostdin",
            "-v",
            "error",
            "-y",
            "-i",
            audio_path,
            "-t",
            str(MAX_AUDIO_SECONDS),
            "-ac",
            "1",
            "-ar",
            str(SAMPLE_RATE),
            *filters.split(),
            "-f",
            "wav",
            converted.name,
        ]
        result = subprocess.run(command, capture_output=True, text=True)
        if result.returncode:
            detail = result.stderr.strip().splitlines()
            raise ValueError(detail[-1] if detail else "Could not decode audio.")

        audio, sample_rate = sf.read(converted.name, dtype="float32")

    if audio.size == 0:
        raise ValueError("The uploaded recording is empty.")
    return np.asarray(audio, dtype=np.float32), sample_rate


def split_audio(audio, sample_rate):
    """Split into short overlapping windows for stable CTC inference."""
    max_samples = MAX_CHUNK_SECONDS * sample_rate
    overlap_samples = CHUNK_OVERLAP_SECONDS * sample_rate
    total_samples = len(audio)

    if total_samples <= max_samples:
        return [audio]

    stride_limit = max_samples - overlap_samples
    chunk_count = (total_samples - overlap_samples + stride_limit - 1) // stride_limit
    chunk_samples = (
        total_samples + (chunk_count - 1) * overlap_samples + chunk_count - 1
    ) // chunk_count
    stride_samples = chunk_samples - overlap_samples

    chunks = []
    for index in range(chunk_count):
        start = index * stride_samples
        end = min(start + chunk_samples, total_samples)
        if start < total_samples:
            chunks.append(audio[start:end])
    return chunks


def is_silent(chunk) -> bool:
    """True when a window is near silence (hallucination risk for whisper)."""
    return float(np.sqrt(np.mean(np.square(chunk)))) < SILENCE_RMS
