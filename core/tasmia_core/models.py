"""Shared data models for the Tasmia core.

This module is intentionally dependency free.  Every other layer (the AI
service, the Go backend and the frontend) ultimately speaks the JSON produced
by :meth:`SessionResult.to_dict`.
"""

from __future__ import annotations


from dataclasses import dataclass
from enum import Enum
# ---------------------------------------------------------------------------
# Status vocabulary
# ---------------------------------------------------------------------------

STATUS_OK = "ok"
STATUS_MISSING = "missing"
STATUS_WRONG = "wrong"
STATUS_MISPRONOUNCED = "mispronounced"
STATUS_REPEATED = "repeated"
STATUS_UNCERTAIN = "uncertain"
STATUS_EXTRA = "extra"

#: Stable order used by API responses and dashboards.
ALL_STATUSES: tuple[str, ...] = (
    STATUS_OK,
    STATUS_MISSING,
    STATUS_WRONG,
    STATUS_MISPRONOUNCED,
    STATUS_REPEATED,
    STATUS_UNCERTAIN,
    STATUS_EXTRA,
)

#: The statuses that can be attached to an expected word.
WORD_STATUSES: tuple[str, ...] = (
    STATUS_OK,
    STATUS_MISSING,
    STATUS_WRONG,
    STATUS_MISPRONOUNCED,
    STATUS_REPEATED,
    STATUS_UNCERTAIN,
)


def empty_counts() -> dict[str, int]:
    """Return a counts dictionary containing every known status."""

    return {status: 0 for status in ALL_STATUSES}


# ---------------------------------------------------------------------------
# Input models
# ---------------------------------------------------------------------------


class kinds_checks(Enum):
    with_tashkeel = "standard"
    without_tashkeel = "remove_tashkeel"
    with_warsh = "warsh"


@dataclass(frozen=True, slots=True)
class Word:
    """One expected word from the Quran.

    ``text`` is the display form (with tashkeel).  ``normalized`` is the
    matching form produced by :mod:`tasmia_core.normalize`.
    """

    text: str
    normalized: str
    surah: int
    ayah: int
    index: int

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "normalized": self.normalized,
            "surah": self.surah,
            "ayah": self.ayah,
            "index": self.index,
        }


@dataclass(frozen=True, slots=True)
class HeardWord:
    """One word produced by the speech recognizer."""

    text: str
    normalized: str
    start: float = 0.0
    end: float = 0.0
    probability: float = 1.0

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "normalized": self.normalized,
            "start": self.start,
            "end": self.end,
            "probability": self.probability,
        }


# ---------------------------------------------------------------------------
# Result models
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class WordResult:
    """The result for one expected word.

    ``index`` is the word's position inside its ayah, not its position in the
    flattened passage.  The API keeps both because the UI can group results by
    ayah.
    """

    expected: str
    heard: str | None
    status: str
    ayah: int
    index: int
    start: float | None = None
    end: float | None = None
    probability: float | None = None
    distance: int | None = None

    def to_dict(self) -> dict:
        return {
            "expected": self.expected,
            "heard": self.heard,
            "status": self.status,
            "ayah": self.ayah,
            "index": self.index,
            "start": self.start,
            "end": self.end,
            "probability": self.probability,
            "distance": self.distance,
        }


@dataclass(frozen=True, slots=True)
class ExtraResult:
    """A heard word that has no matching expected word

    ``after_index`` is the index of the expected word after which the extra
    occurred.  It is ``-1`` when the extra occurred before the first expected
    word.  This makes it possible for the UI to place the extra in the right
    position
    """

    text: str
    status: str = STATUS_EXTRA
    start: float | None = None
    end: float | None = None
    probability: float | None = None
    after_index: int = -1

    def to_dict(self) -> dict:
        return {
            "text": self.text,
            "status": self.status,
            "start": self.start,
            "end": self.end,
            "probability": self.probability,
            "after_index": self.after_index,
        }


@dataclass(slots=True)
class AlignResult:
    """The output of the word level alignment"""

    words: list[WordResult]
    extras: list[ExtraResult]
    expected_count: int
    heard_count: int

    def to_dict(self) -> dict:
        return {
            "expected_count": self.expected_count,
            "heard_count": self.heard_count,
            "words": [word.to_dict() for word in self.words],
            "extras": [extra.to_dict() for extra in self.extras],
        }


@dataclass(slots=True)
class SessionResult:
    """A complete, JSON ready result for one recitation attempt."""

    surah: int
    surah_name: str
    ayah_from: int
    ayah_to: int
    score: float
    strict_accuracy: float
    counts: dict[str, int]
    words: list[WordResult]
    extras: list[ExtraResult]
    model: str = ""
    latency_ms: int | None = None
    schema_version: int = 1

    def to_dict(self) -> dict:
        counts = {status: int(self.counts.get(status, 0)) for status in ALL_STATUSES}
        return {
            "schema_version": self.schema_version,
            "surah": self.surah,
            "surah_name": self.surah_name,
            "ayah_from": self.ayah_from,
            "ayah_to": self.ayah_to,
            "score": self.score,
            "strict_accuracy": self.strict_accuracy,
            "counts": counts,
            "total_words": len(self.words),
            "words": [word.to_dict() for word in self.words],
            "extras": [extra.to_dict() for extra in self.extras],
            "model": self.model,
            "latency_ms": self.latency_ms,
        }
