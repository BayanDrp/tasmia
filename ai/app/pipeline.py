"""Judge a recitation: transcript in, per-word verdicts and score out.

The conductor: this file only orchestrates core calls (mushaf lookup,
alignment, session building); all intelligence lives in core.
"""

from __future__ import annotations

from tasmia_core.align import align
from tasmia_core.models import HeardWord, kinds_checks
from tasmia_core.normalize import normalize_word
from tasmia_core.score import build_session_result
from tasmia_core.surahs import QuranRepository

# The mushaf, loaded once for the whole service.
QURAN = QuranRepository.load()


def evaluate(
    transcript: str,
    surah: int,
    ayah_from: int,
    ayah_to: int | None = None,
    mode: kinds_checks = kinds_checks.without_tashkeel,
    model: str = "",
) -> dict:
    """Judge a recitation: expected mushaf words in, per-word verdicts and score out."""
    if mode is not kinds_checks.without_tashkeel:
        raise NotImplementedError(f"mode '{mode.value}' is under development")

    expected = QURAN.expected_words(surah, ayah_from, ayah_to, include_basmala=False)

    # THE mode hook: without_tashkeel strips diacritics via normalize_word.
    # Future modes change how `normalized` is filled; nothing else moves.
    heard = [
        HeardWord(text=word, normalized=normalize_word(word))
        for word in transcript.split()
    ]

    align_result = align(expected, heard)

    session = build_session_result(
        surah=surah,
        surah_name=QURAN.get_surah(surah).name,
        ayah_from=ayah_from,
        ayah_to=ayah_to,
        align_result=align_result,
        model=model,
    )
    return session.to_dict()
