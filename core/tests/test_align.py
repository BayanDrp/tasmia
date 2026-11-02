"""Tests for tasmia_core.align."""

from __future__ import annotations

import unittest

from tasmia_core.align import align, apply_tashkeel_check
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


class TashkeelCheckTests(unittest.TestCase):
    """The checked mode: base letters match, basic vowels decide."""

    def test_vowel_error_becomes_mispronounced(self):
        result = align([word("أَلَمْ")], [heard("أَلِمْ")])
        self.assertEqual(result.words[0].status, "ok")
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[0].status, "mispronounced")

    def test_matching_vowels_stay_ok(self):
        result = align([word("أَلَمْ")], [heard("اَلَمْ")])
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[0].status, "ok")

    def test_missing_final_vowel_becomes_mispronounced(self):
        result = align([word("صَدْرَكَ")], [heard("صَدْرَك")])
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[0].status, "mispronounced")

    def test_shadda_is_ignored(self):
        result = align([word("رَبِّ")], [heard("رَبِ")])
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[0].status, "ok")

    def test_warsh_orthography_is_tolerated(self):
        result = align([word("اَ۬لذِےٓ")], [heard("الَّذِي")])
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[0].status, "ok")

    def test_fused_split_keeps_raw_hearing(self):
        expected = [
            word("وِزْرَكَ", index=0),
            word("اَ۬لذِےٓ", index=1),
        ]
        result = align(expected, [heard("وِزْرَكَالَّذِي")])
        self.assertEqual(result.words[1].heard, "الَّذِي")
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[1].status, "ok")

    def test_non_ok_status_is_unchanged(self):
        result = align([word("مَعَ")], [heard("فَإِنَّمَا")])
        original = result.words[0].status
        self.assertNotEqual(original, "ok")
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.words[0].status, original)

    def test_counts_and_extras_are_preserved(self):
        result = align(
            [word("قُلْ"), word("هُوَ")],
            [heard("قُلْ"), heard("هُوَ"), heard("زَائِد")],
        )
        checked = apply_tashkeel_check(result)
        self.assertEqual(checked.expected_count, result.expected_count)
        self.assertEqual(checked.heard_count, result.heard_count)
        self.assertEqual(len(checked.extras), len(result.extras))


if __name__ == "__main__":
    unittest.main()
