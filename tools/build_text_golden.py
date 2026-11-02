#!/usr/bin/env python3
"""Regenerate the Go text parity golden from core.

The web reader (web/backend/reader.go) is a Go port of core's word
splitter. This script asks core itself for every surah's display words
and writes them to web/backend/tests/testdata/quran_text_golden.json.
The Go test compares the reader against that file, so a drift between
the two splitters fails the build instead of reaching the screen.

Run: make web-golden
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "core"))

from tasmia_core.surahs import QuranRepository  # noqa: E402


def main() -> None:
    quran = QuranRepository.load()
    golden: dict[str, list[dict]] = {}

    for number in range(1, 115):
        words = quran.expected_words(number, 1, None, include_basmala=False)
        golden[str(number)] = [
            {"ayah": word.ayah, "text": word.text} for word in words
        ]

    dest = ROOT / "web" / "backend" / "tests" / "testdata" / "quran_text_golden.json"
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(
        json.dumps(golden, ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )

    total = sum(len(words) for words in golden.values())
    print(f"wrote {dest.relative_to(ROOT)}: 114 surahs, {total} words")


if __name__ == "__main__":
    main()
