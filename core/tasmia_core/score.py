"""Scoring for a recitation session.

Turns an :class:`~tasmia_core.align.AlignResult` into a session-level
result: weighted score, strict accuracy, per status counts, and a
JSON-ready :class:`~tasmia_core.models.SessionResult`.

Weights (per expected word):

    ok           -> 1.0   correct recitation
    mispronounced-> 0.75  close but not exact (weak-letter match)
    uncertain    -> 0.5   low model confidence
    wrong        -> 0     clearly wrong
    missing      -> 0     expected word not recited
    repeated     -> 0     duplicate of an already-recited word

Extra (heard-only) words do not affect the score.
"""

from __future__ import annotations

from dataclasses import replace

from .align import AlignResult
from .models import (
    SessionResult,
    STATUS_EXTRA,
    STATUS_MISSING,
    STATUS_MISPRONOUNCED,
    STATUS_OK,
    STATUS_REPEATED,
    STATUS_UNCERTAIN,
    STATUS_WRONG,
    empty_counts,
)

#: Points awarded for each expected-word status.  Extras are scored
#: separately and do not enter the weighted average.
STATUS_WEIGHTS: dict[str, float] = {
    STATUS_OK: 1.0,
    STATUS_MISPRONOUNCED: 0.75,
    STATUS_UNCERTAIN: 0.5,
    STATUS_WRONG: 0.0,
    STATUS_MISSING: 0.0,
    STATUS_REPEATED: 0.0,
}


def score_align_result(result: AlignResult) -> dict:
    """Compute score, strict accuracy and counts from an alignment result.

    Returns a dict with ``score``, ``strict_accuracy`` and ``counts``.
    """

    counts = empty_counts()
    total = len(result.words)

    weighted_sum = 0.0
    ok_count = 0

    for word in result.words:
        status = word.status
        counts[status] = counts.get(status, 0) + 1
        weighted_sum += STATUS_WEIGHTS.get(status, 0.0)
        if status == STATUS_OK:
            ok_count += 1

    score = weighted_sum / total if total else 0.0
    strict_accuracy = ok_count / total if total else 0.0

    # Extras are tracked in counts but excluded from the score denominator.
    for extra in result.extras:
        counts[STATUS_EXTRA] = counts.get(STATUS_EXTRA, 0) + 1

    return {
        "score": round(score, 4),
        "strict_accuracy": round(strict_accuracy, 4),
        "counts": counts,
        "total_words": total,
        "heard_words": result.heard_count,
    }


def build_session_result(
    *,
    surah: int,
    surah_name: str,
    ayah_from: int,
    ayah_to: int,
    align_result: AlignResult,
    model: str = "",
    latency_ms: int | None = None,
) -> SessionResult:
    """Build a complete :class:`SessionResult` from an alignment result."""

    scored = score_align_result(align_result)

    return SessionResult(
        surah=surah,
        surah_name=surah_name,
        ayah_from=ayah_from,
        ayah_to=ayah_to,
        score=scored["score"],
        strict_accuracy=scored["strict_accuracy"],
        counts=scored["counts"],
        words=list(align_result.words),
        extras=list(align_result.extras),
        model=model,
        latency_ms=latency_ms,
    )
