"""Judge a recitation: transcript in, per word verdicts and score out.

The conductor: this file only orchestrates core calls (mushaf lookup,
alignment, session building); all intelligence lives in core.
"""

from __future__ import annotations

from tasmia_core.align import align, apply_tashkeel_check
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
    """Judge a recitation: expected mushaf words in, per word verdicts and score out."""
    expected = QURAN.expected_words(surah, ayah_from, ayah_to, include_basmala=False)

    # The base alignment always compares stripped forms. The checked
    # modes add a second pass over the basic vowel pattern; the alignment
    # itself stays the same.
    heard = [
        HeardWord(text=word, normalized=normalize_word(word))
        for word in transcript.split()
    ]

    align_result = align(expected, heard)
    if mode is kinds_checks.with_tashkeel or mode is kinds_checks.with_warsh:
        # `with_warsh` currently shares the basic vowel check. A true
        # Warsh comparison (imala, madd, etc.) is a later mode.
        align_result = apply_tashkeel_check(align_result)

    session = build_session_result(
        surah=surah,
        surah_name=QURAN.get_surah(surah).name,
        ayah_from=ayah_from,
        ayah_to=ayah_to,
        align_result=align_result,
        model=model,
    )
    return session.to_dict()
