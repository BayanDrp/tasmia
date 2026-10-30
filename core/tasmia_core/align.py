"""Word level alignment of expected Quran words with ASR output."""

from __future__ import annotations

from dataclasses import dataclass, replace

from .models import (
    AlignResult,
    ExtraResult,
    HeardWord,
    Word,
    WordResult,
    STATUS_EXTRA,
    STATUS_MISPRONOUNCED,
    STATUS_MISSING,
    STATUS_OK,
    STATUS_REPEATED,
    STATUS_UNCERTAIN,
    STATUS_WRONG,
)
from .normalize import normalize_word, weak_letter_key


_INF = 10**15
_DIAG = 0
_UP = 1
_LEFT = 2


@dataclass(frozen=True, slots=True)
class AlignConfig:
    gap_cost: int = 2
    weak_cost: int = 1
    mismatch_cost: int = 3
    uncertain_below: float = 0.45
    confident_at: float = 0.60
    mispronounced_similarity: float = 0.75
    detect_repetitions: bool = True
    band_margin: int = 40


def _validate_config(config: AlignConfig) -> None:
    if config.gap_cost < 0:
        raise ValueError("gap_cost must be non negative")
    if config.weak_cost < 0:
        raise ValueError("weak_cost must be non negative")
    if config.mismatch_cost < 0:
        raise ValueError("mismatch_cost must be non negative")
    if not 0.0 <= config.uncertain_below <= 1.0:
        raise ValueError("uncertain_below must be between 0 and 1")
    if not 0.0 <= config.confident_at <= 1.0:
        raise ValueError("confident_at must be between 0 and 1")
    if config.uncertain_below > config.confident_at:
        raise ValueError("uncertain_below must not be greater than confident_at")
    if not 0.0 <= config.mispronounced_similarity <= 1.0:
        raise ValueError("mispronounced_similarity must be between 0 and 1")
    if not isinstance(config.band_margin, int) or config.band_margin < 0:
        raise ValueError("band_margin must be a non negative integer")


def _prepare_expected(expected: list[Word]) -> tuple[list[str], list[str]]:
    normalized_words: list[str] = []
    weak_keys: list[str] = []

    for word in expected:
        normalized = word.normalized or normalize_word(word.text)
        if not normalized:
            raise ValueError(
                f"expected word {word!r} has an empty normalized form"
            )
        normalized_words.append(normalized)
        weak_keys.append(weak_letter_key(normalized))

    return normalized_words, weak_keys


def _prepare_heard(
    heard: list[HeardWord],
) -> tuple[list[HeardWord], list[str], list[str]]:
    words: list[HeardWord] = []
    normalized_words: list[str] = []
    weak_keys: list[str] = []

    for word in heard:
        normalized = word.normalized or normalize_word(word.text)
        if not normalized:
            continue
        words.append(word)
        normalized_words.append(normalized)
        weak_keys.append(weak_letter_key(normalized))

    return words, normalized_words, weak_keys


def _probability(word: HeardWord) -> float:
    probability = word.probability
    if probability is None:
        return 1.0
    return max(0.0, min(1.0, float(probability)))


def _levenshtein(left: str, right: str) -> int:
    """Return the edit distance between two normalized words."""

    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    if len(left) < len(right):
        left, right = right, left

    previous = list(range(len(right) + 1))
    for row, left_char in enumerate(left, start=1):
        current = [row]
        for column, right_char in enumerate(right, start=1):
            insert = current[column - 1] + 1
            delete = previous[column] + 1
            substitute = previous[column - 1] + (left_char != right_char)
            current.append(min(insert, delete, substitute))
        previous = current

    return previous[-1]


def _similarity(expected: str, heard: str, distance: int) -> float:
    longest = max(len(expected), len(heard))
    if longest == 0:
        return 0.0
    return 1.0 - (distance / longest)


def _classify_pair(
    expected_normalized: str,
    expected_weak: str,
    heard_word: HeardWord,
    heard_normalized: str,
    heard_weak: str,
    config: AlignConfig,
) -> tuple[str, int]:
    """Classify one matched expected/heard pair."""

    if expected_normalized == heard_normalized:
        kind = "exact"
    elif expected_weak == heard_weak:
        kind = "weak"
    else:
        kind = "mismatch"

    distance = _levenshtein(expected_normalized, heard_normalized)
    probability = _probability(heard_word)

    if kind == "exact":
        if probability < config.uncertain_below:
            return STATUS_UNCERTAIN, distance
        return STATUS_OK, distance

    if probability < config.confident_at:
        return STATUS_UNCERTAIN, distance

    similarity = _similarity(expected_normalized, heard_normalized, distance)

    if kind == "weak":
        # A weak match can be very short, so do not call every weak-key
        # collision a pronunciation error.
        if similarity >= 0.60:
            return STATUS_MISPRONOUNCED, distance
        return STATUS_WRONG, distance

    if similarity >= config.mispronounced_similarity:
        return STATUS_MISPRONOUNCED, distance
    return STATUS_WRONG, distance


def _align_banded(
    expected_normalized: list[str],
    expected_weak: list[str],
    heard_normalized: list[str],
    heard_weak: list[str],
    config: AlignConfig,
    band: int,
) -> tuple[list[tuple[str, int | None, int | None]], bool] | None:
    """Run one banded DP pass.

    Returns ``(operations, touched_band_edge)`` or ``None`` if the final
    cell is not reachable with this band.
    """

    expected_count = len(expected_normalized)
    heard_count = len(heard_normalized)

    lows = [0] * (expected_count + 1)
    highs = [0] * (expected_count + 1)
    backs: list[bytearray | None] = [None] * (expected_count + 1)

    previous: list[int] = []
    previous_low = 0
    previous_high = -1

    for row_number in range(expected_count + 1):
        low = max(0, row_number - band)
        high = min(heard_count, row_number + band)
        if low > high:
            return None

        lows[row_number] = low
        highs[row_number] = high
        row = [_INF] * (high - low + 1)

        if row_number == 0:
            for column in range(low, high + 1):
                row[column - low] = column * config.gap_cost
        else:
            back = bytearray(high - low + 1)

            if low == 0:
                row[0] = row_number * config.gap_cost
                back[0] = _UP

            for column in range(max(1, low), high + 1):
                expected_index = row_number - 1
                heard_index = column - 1

                if previous_low <= column - 1 <= previous_high:
                    expected = expected_normalized[expected_index]
                    heard = heard_normalized[heard_index]
                    if expected == heard:
                        pair_cost = 0
                    elif expected_weak[expected_index] == heard_weak[heard_index]:
                        pair_cost = config.weak_cost
                    else:
                        pair_cost = config.mismatch_cost
                    diagonal = (
                        previous[(column - 1) - previous_low] + pair_cost
                    )
                else:
                    diagonal = _INF

                if previous_low <= column <= previous_high:
                    up = previous[column - previous_low] + config.gap_cost
                else:
                    up = _INF

                if column - 1 >= low:
                    left = row[(column - 1) - low] + config.gap_cost
                else:
                    left = _INF

                if diagonal <= up and diagonal <= left:
                    row[column - low] = diagonal
                    back[column - low] = _DIAG
                elif up <= left:
                    row[column - low] = up
                    back[column - low] = _UP
                else:
                    row[column - low] = left
                    back[column - low] = _LEFT

            backs[row_number] = back

        previous = row
        previous_low = low
        previous_high = high

    if not (lows[expected_count] <= heard_count <= highs[expected_count]):
        return None

    final_index = heard_count - lows[expected_count]
    if previous[final_index] >= _INF // 2:
        return None

    operations: list[tuple[str, int | None, int | None]] = []
    row_number = expected_count
    column = heard_count
    touched_edge = False
    maximum_dimension = max(expected_count, heard_count)

    while row_number > 0 or column > 0:
        if row_number == 0:
            operations.append(("insert", None, column - 1))
            column -= 1
            continue

        if column == 0:
            operations.append(("delete", row_number - 1, None))
            row_number -= 1
            continue

        low = lows[row_number]
        high = highs[row_number]
        if not (low <= column <= high):
            return None

        if (
            band < maximum_dimension
            and 0 < row_number < expected_count
            and 0 < column < heard_count
            and (column == low or column == high)
        ):
            touched_edge = True

        back = backs[row_number]
        if back is None:
            return None

        choice = back[column - low]
        if choice == _DIAG:
            operations.append(("pair", row_number - 1, column - 1))
            row_number -= 1
            column -= 1
        elif choice == _UP:
            operations.append(("delete", row_number - 1, None))
            row_number -= 1
        else:
            operations.append(("insert", None, column - 1))
            column -= 1

    operations.reverse()
    return operations, touched_edge


def _align_operations(
    expected_normalized: list[str],
    expected_weak: list[str],
    heard_normalized: list[str],
    heard_weak: list[str],
    config: AlignConfig,
) -> list[tuple[str, int | None, int | None]]:
    expected_count = len(expected_normalized)
    heard_count = len(heard_normalized)
    maximum_dimension = max(expected_count, heard_count)

    band = max(
        abs(expected_count - heard_count) + config.band_margin,
        int(0.05 * maximum_dimension),
        32,
    )
    band = min(band, maximum_dimension)

    while True:
        result = _align_banded(
            expected_normalized,
            expected_weak,
            heard_normalized,
            heard_weak,
            config,
            band,
        )

        if result is None:
            if band >= maximum_dimension:
                raise RuntimeError("unable to align the expected and heard words")
            band = min(maximum_dimension, band * 2)
            continue

        operations, touched_edge = result
        if touched_edge and band < maximum_dimension:
            band = min(maximum_dimension, band * 2)
            continue

        return operations


def _build_results(
    operations: list[tuple[str, int | None, int | None]],
    expected: list[Word],
    expected_normalized: list[str],
    expected_weak: list[str],
    heard: list[HeardWord],
    heard_normalized: list[str],
    heard_weak: list[str],
    config: AlignConfig,
) -> tuple[list[WordResult], list[ExtraResult]]:
    words: list[WordResult] = []
    extras: list[ExtraResult] = []
    last_expected_index = -1

    for kind, expected_index, heard_index in operations:
        if kind == "pair":
            assert expected_index is not None
            assert heard_index is not None
            expected_word = expected[expected_index]
            heard_word = heard[heard_index]
            status, distance = _classify_pair(
                expected_normalized[expected_index],
                expected_weak[expected_index],
                heard_word,
                heard_normalized[heard_index],
                heard_weak[heard_index],
                config,
            )
            words.append(
                WordResult(
                    expected=expected_word.text,
                    heard=heard_word.text,
                    status=status,
                    ayah=expected_word.ayah,
                    index=expected_word.index,
                    start=heard_word.start,
                    end=heard_word.end,
                    probability=_probability(heard_word),
                    distance=distance,
                )
            )
            last_expected_index = expected_index
        elif kind == "delete":
            assert expected_index is not None
            expected_word = expected[expected_index]
            words.append(
                WordResult(
                    expected=expected_word.text,
                    heard=None,
                    status=STATUS_MISSING,
                    ayah=expected_word.ayah,
                    index=expected_word.index,
                )
            )
            last_expected_index = expected_index
        else:
            assert heard_index is not None
            heard_word = heard[heard_index]
            extras.append(
                ExtraResult(
                    text=heard_word.text,
                    status=STATUS_EXTRA,
                    start=heard_word.start,
                    end=heard_word.end,
                    probability=_probability(heard_word),
                    after_index=last_expected_index,
                )
            )

    return words, extras


def _mark_repetitions(
    words: list[WordResult],
    extras: list[ExtraResult],
    expected_normalized: list[str],
    config: AlignConfig,
) -> None:
    for extra in extras:
        extra_normalized = normalize_word(extra.text)
        if not extra_normalized:
            continue

        # An extra can be a duplicate of the word before it or the word after
        # it.  The DP often treats the first occurrence as the extra and
        # matches the second one, especially at the beginning of a passage.
        candidates: list[int] = []
        if extra.after_index >= 0:
            candidates.append(extra.after_index)
        if extra.after_index + 1 < len(words):
            candidates.append(extra.after_index + 1)

        target_index: int | None = None
        for candidate in candidates:
            if not 0 <= candidate < len(words):
                continue
            if extra_normalized != expected_normalized[candidate]:
                continue
            candidate_word = words[candidate]
            if candidate_word.status not in (STATUS_OK, STATUS_MISPRONOUNCED):
                continue
            target_index = candidate
            break

        if target_index is None:
            continue

        previous = words[target_index]

        extra_probability = (
            extra.probability if extra.probability is not None else 1.0
        )
        if extra_probability < config.confident_at:
            continue

        previous_probability = (
            previous.probability if previous.probability is not None else 1.0
        )
        if extra.probability is not None:
            previous_probability = min(
                previous_probability,
                extra.probability,
            )

        words[target_index] = replace(
            previous,
            status=STATUS_REPEATED,
            end=extra.end if extra.end is not None else previous.end,
            probability=previous_probability,
        )


def _repair_heard_tokens(expected: list[Word], heard: list[HeardWord]) -> list[HeardWord]:
    """Rescue ASR tokenization artifacts before alignment.

    Two exact-match repairs, both guided by the mushaf:

    * fusion: one heard token is the exact concatenation of two
      consecutive expected words (the model forgot a space), e.g.
      وِزْرَكَالَّذِي for وِزْرَكَ + الَّذِي -> split it back in two.
    * split: two consecutive heard tokens concatenate to exactly one
      expected word (the model inserted a space) -> merge them.

    Only exact normalized concatenations trigger a repair, so genuine
    mispronunciations pass through untouched.  A token whose normalized
    form is itself a single expected word is never split: the single
    word is the safer reading.
    """
    if not heard or not expected:
        return list(heard)

    expected_norm = [word.normalized or normalize_word(word.text) for word in expected]
    single = {norm for norm in expected_norm if norm}

    # normalized concat of two consecutive expected words -> their norms
    fusion_of: dict[str, tuple[str, str]] = {}
    for first, second in zip(expected_norm, expected_norm[1:]):
        if first and second and (first + second) not in single:
            fusion_of.setdefault(first + second, (first, second))

    # display text of each expected norm (cosmetic; alignment uses norms)
    display: dict[str, str] = {}
    for word in expected:
        display.setdefault(word.normalized or normalize_word(word.text), word.text)

    repaired: list[HeardWord] = []
    index = 0
    while index < len(heard):
        word = heard[index]
        norm = word.normalized or normalize_word(word.text)
        nxt = heard[index + 1] if index + 1 < len(heard) else None

        if nxt is not None:
            nxt_norm = nxt.normalized or normalize_word(nxt.text)
            together = norm + nxt_norm
            # two heard tokens, one expected word (and no rival reading)
            if norm and nxt_norm and together in single and together not in fusion_of:
                repaired.append(
                    HeardWord(
                        text=f"{word.text} {nxt.text}",
                        normalized=together,
                        start=word.start,
                        end=nxt.end,
                        probability=min(word.probability, nxt.probability),
                    )
                )
                index += 2
                continue

        # one heard token, two expected words: both halves share the
        # fused token's timing and probability.
        parts = fusion_of.get(norm) if norm else None
        if parts:
            for part in parts:
                repaired.append(
                    HeardWord(
                        text=display.get(part, part),
                        normalized=part,
                        start=word.start,
                        end=word.end,
                        probability=word.probability,
                    )
                )
            index += 1
            continue

        repaired.append(word)
        index += 1

    return repaired


def align(
    expected: list[Word],
    heard: list[HeardWord],
    config: AlignConfig | None = None,
) -> AlignResult:
    """Align expected Quran words with words produced by the ASR.

    Every expected word produces one :class:`WordResult`.  Heard words that
    have no expected counterpart are returned as :class:`ExtraResult` objects.

    ``ExtraResult.after_index`` is the global, zero based index of the last
    expected word before the extra.  It is ``-1`` when the extra occurs
    before the first expected word.
    """

    active_config = config or AlignConfig()
    _validate_config(active_config)

    if not expected:
        raise ValueError("expected must contain at least one word")

    expected_words = list(expected)
    heard = _repair_heard_tokens(expected_words, heard)

    expected_normalized, expected_weak = _prepare_expected(expected_words)
    heard_words, heard_normalized, heard_weak = _prepare_heard(heard)

    if heard_words:
        operations = _align_operations(
            expected_normalized,
            expected_weak,
            heard_normalized,
            heard_weak,
            active_config,
        )
    else:
        operations = [
            ("delete", index, None)
            for index in range(len(expected_words))
        ]

    words, extras = _build_results(
        operations,
        expected_words,
        expected_normalized,
        expected_weak,
        heard_words,
        heard_normalized,
        heard_weak,
        active_config,
    )

    if active_config.detect_repetitions:
        _mark_repetitions(
            words,
            extras,
            expected_normalized,
            active_config,
        )

    return AlignResult(
        words=words,
        extras=extras,
        expected_count=len(expected_words),
        heard_count=len(heard_words),
    )


__all__ = ["AlignConfig", "align"]
