

import unicodedata


_LETTER_MAP = str.maketrans(
    {
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
        "ٱ": "ا",
        "ٲ": "ا",
        "ٳ": "ا",
        "ى": "ي",
        "ة": "ه",
        "ؤ": "و",
        "ئ": "ي",
        "ء": "",
        "ٴ": "",
        "ک": "ك",
        "ی": "ي",
        "ے": "ي",
        "ہ": "ه",
    }
)

_DIGIT_MAP = str.maketrans(
    "٠١٢٣٤٥٦٧٨٩۰۱۲۳۴۵۶۷۸۹",
    "01234567890123456789",
)


def strip_tashkeel(text: str) -> str:
    """Remove Arabic diacritics and Quranic annotation marks."""
    return "".join(
        char
        for char in text
        if not (
            "\u0610" <= char <= "\u061A"    # honorifics
            or "\u064B" <= char <= "\u065F" # tashkeel
            or char == "\u0670"             # superscript alef
            or "\u06D6" <= char <= "\u06ED" # Quranic small-high marks
            or "\u06DD" <= char <= "\u06DE" # end of ayah / rub el hizb
            or "\u0897" <= char <= "\u089F" # Arabic Extended-B
            or "\u08CA" <= char <= "\u08FF" # Arabic Extended-A
            or "\U00010EFC" <= char <= "\U00010EFF"  # Arabic Extended-C
        )
    )

def normalize_word(word: str) -> str:
    """Normalize one word for matching."""
    # The Warsh mushaf writes the madd with a superscript alef (U+0670)
    # while the ASR writes a full alef; treat the superscript alef as a
    # regular alef so both spellings match exactly.
    text = word.replace("\u0670", "\u0627")
    text = strip_tashkeel(text).replace("\u0640", "")
    text = text.translate(_LETTER_MAP).translate(_DIGIT_MAP)
    text = "".join(
        char
        for char in text
        if not unicodedata.category(char).startswith(("P", "S", "M", "Z", "C"))
    )
    return "".join(text.split())


# Basic vowel marks compared by the tashkeel mode. Shadda is excluded:
# Warsh and Hafs orthography mark gemination differently, and the ASR
# often omits it. Quranic annotation marks are also excluded.
_TASHKEEL_MARKS = frozenset("\u064B\u064C\u064D\u064E\u064F\u0650\u0652")


def tashkeel_pattern(word: str) -> str:
    """Return the ordered basic vowel marks of one word.

    The base letters are aligned separately. This pattern keeps the short
    vowels, tanween and sukun, drops shadda and Quranic marks, and ignores
    which letter carries the mark. That makes it tolerant of Warsh/Hafs
    orthography differences such as the fatha on the definite article.
    """
    return "".join(char for char in word if char in _TASHKEEL_MARKS)


def normalize_text(text: str) -> str:
    """Normalize a phrase for matching, preserving word order."""
    return " ".join(
        normalized
        for token in text.split()
        if (normalized := normalize_word(token))
    )


_WEAK_LETTERS = frozenset("اوي")


def _weak_key_from_normalized(normalized: str) -> str:
    key = "".join(char for char in normalized if char not in _WEAK_LETTERS)
    return key or normalized


def weak_letter_key(word: str) -> str:
    """Return a matching key that ignores alef, waw, and ya."""
    return _weak_key_from_normalized(normalize_word(word))


def word_match(expected: str, heard: str) -> str:
    """Classify two words as 'exact', 'weak', or 'mismatch'."""
    expected_normalized = normalize_word(expected)
    heard_normalized = normalize_word(heard)

    if not expected_normalized or not heard_normalized:
        return "mismatch"

    if expected_normalized == heard_normalized:
        return "exact"

    expected_key = _weak_key_from_normalized(expected_normalized)
    heard_key = _weak_key_from_normalized(heard_normalized)

    if expected_key == heard_key:
        return "weak"

    return "mismatch"


def display_word(word: str) -> str:
    """Clean one token for display while preserving Quranic orthography."""
    text = word.replace("\u0640", "")

    text = "".join(
        char
        for char in text
        if not (
            "\u0610" <= char <= "\u061A"  # honorifics
            or "\u06D6" <= char <= "\u06E4"  # Quranic pause/annotation marks
            or "\u06E7" <= char <= "\u06E9"  # small high yeh/noon, sajdah
            or char == "\u06ED"  # small low meem
            # Keep U+06E5/U+06E6 (small waw/yeh) and U+06EA-U+06EC
            # because Warsh uses them as part of the written text.
            or "\u0897" <= char <= "\u089F"  # Arabic Extended-B
            or "\u08CA" <= char <= "\u08FF"  # Arabic Extended-A
            or "\U00010EFC" <= char <= "\U00010EFF"  # Arabic Extended-C
        )
    )

    text = "".join(
        char
        for char in text
        if not unicodedata.category(char).startswith(("P", "S", "Z", "C"))
    )

    return text.strip()


def display_tokens(text: str) -> list[str]:
    """Return clean display words for the UI, preserving word order."""
    return [
        word
        for token in tokenize(text)
        if (word := display_word(token))
    ]

def tokenize(text: str) -> list[str]:
    return [token for token in text.split() if token]


def normalize(text: str) -> str:
    """Backward-compatible alias for normalize_text()."""
    return normalize_text(text)


def merge_chunk_texts(texts: list[str]) -> str:
    """Join chunk transcripts while removing repeated seam words.

    Chunked ASR with overlapping windows repeats the words that fall in the
    overlap; the join drops the repetition by matching the longest normalized
    run at the seam.
    """
    merged: list[str] = []

    for text in texts:
        words = text.split()
        if not words:
            continue

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

def collapse_repetition(text: str, max_repeat: int = 10) -> str:
    """Collapse words repeated in a row beyond max_repeat.

    ASR engines sometimes get stuck and emit one word hundreds of times
    (whisper loops on trailing noise). Real recitation never contains one
    word max_repeat times consecutively, so keeping the first max_repeat
    copies of a run can never damage honest text.
    """
    words = text.split()
    collapsed: list[str] = []
    run = 0
    for word in words:
        if collapsed and word == collapsed[-1]:
            run += 1
        else:
            run = 0
        if run < max_repeat:
            collapsed.append(word)
    return " ".join(collapsed)
