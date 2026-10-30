"""Tests for tasmia_core.align."""

from __future__ import annotations

import unittest

from tasmia_core.align import align
from tasmia_core.models import HeardWord, Word
from tasmia_core.normalize import normalize_word


def word(text: str, ayah: int = 1, index: int = 0) -> Word:
    return Word(
        text=text,
        normalized=normalize_word(text),
        surah=94,
        ayah=ayah,
        index=index,
    )


def heard(text: str) -> HeardWord:
    return HeardWord(text=text, normalized=normalize_word(text))


class FusionRepairTests(unittest.TestCase):
    """The tokenizer repair pass: fused and split model output."""

    def test_fused_heard_word_is_split_and_matched(self):
        expected = [
            word("صَدْرَكَ", index=0),
            word("وِزْرَكَ", index=1),
            word("الَّذِي", index=2),
        ]
        heard_list = [heard("صَدْرَكَ"), heard("وِزْرَكَالَّذِي")]
        result = align(expected, heard_list)
        self.assertEqual([w.status for w in result.words], ["ok", "ok", "ok"])
        self.assertEqual(result.words[1].heard, "وِزْرَكَ")
        self.assertEqual(result.extras, [])

    def test_split_heard_words_are_merged(self):
        expected = [word("الْحَمْدُ", index=0), word("لِلَّهِ", index=1)]
        heard_list = [heard("الْحَمْدُ"), heard("لِ"), heard("لَّهِ")]
        result = align(expected, heard_list)
        self.assertEqual([w.status for w in result.words], ["ok", "ok"])
        self.assertEqual(result.extras, [])

    def test_mangled_word_is_not_repaired(self):
        # وَرَفَعْهَا is not an exact concatenation of any expected pair:
        # it stays a mispronunciation (weak match on وَرَفَعْنَا).
        expected = [word("وَرَفَعْنَا", index=0), word("لَكَ", index=1)]
        heard_list = [heard("وَرَفَعْهَا"), heard("لَكَ")]
        result = align(expected, heard_list)
        self.assertEqual(result.words[0].status, "mispronounced")
        self.assertEqual(result.words[0].heard, "وَرَفَعْهَا")

    def test_full_word_is_never_split(self):
        # وَ + ٱللَّهِ concatenates to وَاللَّهِ, which is also a single
        # expected word: the single word is the safer reading, so the
        # token must survive unsplit.
        expected = [
            word("وَ", index=0),
            word("ٱللَّهِ", index=1),
            word("وَاللَّهِ", index=2),
        ]
        heard_list = [heard("وَاللَّهِ")]
        result = align(expected, heard_list)
        self.assertEqual(result.words[2].status, "ok")
        self.assertEqual(result.words[0].status, "missing")
        self.assertEqual(result.words[1].status, "missing")

    def test_perfect_recitation_is_untouched(self):
        expected = [
            word("قُلْ", index=0),
            word("هُوَ", index=1),
            word("ٱللَّهُ", index=2),
        ]
        heard_list = [heard("قُلْ"), heard("هُوَ"), heard("ٱللَّهُ")]
        result = align(expected, heard_list)
        self.assertEqual([w.status for w in result.words], ["ok", "ok", "ok"])
        self.assertEqual(result.extras, [])


if __name__ == "__main__":
    unittest.main()
