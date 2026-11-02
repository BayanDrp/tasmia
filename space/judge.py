"""Judge a transcript with the core vendored inside the Space.

The Space owns both steps now: ASR on the GPU, then alignment and
scoring on the CPU. Render only runs the Go site and calls this Space.
"""

from __future__ import annotations

from pathlib import Path

from tasmia_core.align import align, apply_tashkeel_check
from tasmia_core.models import HeardWord, kinds_checks
from tasmia_core.normalize import normalize_word
from tasmia_core.score import build_session_result
from tasmia_core.surahs import QuranRepository

# The Space is uploaded with the contents of space/ at its root, so the
# data sits next to this file.
QURAN_PATH = Path(__file__).resolve().parent / "data" / "quran" / "quran.json"
QURAN = QuranRepository.load(QURAN_PATH)


def parse_mode(mode: str) -> kinds_checks:
    """Translate a client mode string into the core enum."""
    if not mode:
        return kinds_checks.without_tashkeel
    try:
        return kinds_checks(mode)
    except ValueError as exc:
        raise ValueError(f"unknown mode '{mode}'") from exc


def evaluate(
    transcript: str,
    surah: int,
    ayah_from: int,
    ayah_to: int | None = None,
    mode: kinds_checks = kinds_checks.without_tashkeel,
    model: str = "",
    latency_ms: int | None = None,
) -> dict:
    """Return a complete judged session for one transcript."""
    expected = QURAN.expected_words(
        surah, ayah_from, ayah_to, include_basmala=False
    )

    heard = [
        HeardWord(text=word, normalized=normalize_word(word))
        for word in transcript.split()
    ]

    align_result = align(expected, heard)
    if mode is kinds_checks.with_tashkeel or mode is kinds_checks.with_warsh:
        align_result = apply_tashkeel_check(align_result)

    session = build_session_result(
        surah=surah,
        surah_name=QURAN.get_surah(surah).name,
        ayah_from=ayah_from,
        ayah_to=ayah_to,
        align_result=align_result,
        model=model,
        latency_ms=latency_ms,
    )
    return session.to_dict()
