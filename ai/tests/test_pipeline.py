"""Tests for the judging pipeline and its three recitation modes."""

from __future__ import annotations

import unittest

from app.pipeline import evaluate
from tasmia_core.models import kinds_checks


SURAH = 94
AYAH = 1
GOOD = "أَلَمْ نَشْرَحْ لَكَ صَدْرَكَ"
VOWEL_ERROR = "أَلِمْ نَشْرَحْ لَكَ صَدْرَكَ"
MISSING_FINAL = "أَلَمْ نَشْرَحْ لَكَ صَدْرَك"


class PipelineModeTests(unittest.TestCase):
    def test_fast_mode_ignores_vowels(self):
        result = evaluate(
            VOWEL_ERROR,
            SURAH,
            AYAH,
            AYAH,
            kinds_checks.without_tashkeel,
            "quick",
        )
        self.assertEqual(result["words"][0]["status"], "ok")
        self.assertEqual(result["score"], 1.0)

    def test_checked_mode_marks_vowel_error(self):
        result = evaluate(
            VOWEL_ERROR,
            SURAH,
            AYAH,
            AYAH,
            kinds_checks.with_tashkeel,
            "quick",
        )
        self.assertEqual(result["words"][0]["status"], "mispronounced")
        self.assertLess(result["score"], 1.0)

    def test_checked_mode_accepts_good_recitation(self):
        result = evaluate(
            GOOD,
            SURAH,
            AYAH,
            AYAH,
            kinds_checks.with_tashkeel,
            "quick",
        )
        self.assertEqual([word["status"] for word in result["words"]], ["ok"] * 4)
        self.assertEqual(result["score"], 1.0)

    def test_checked_mode_marks_missing_final_vowel(self):
        result = evaluate(
            MISSING_FINAL,
            SURAH,
            AYAH,
            AYAH,
            kinds_checks.with_tashkeel,
            "quick",
        )
        self.assertEqual(result["words"][-1]["status"], "mispronounced")

    def test_warsh_mode_shares_the_vowel_check_for_now(self):
        checked = evaluate(
            VOWEL_ERROR,
            SURAH,
            AYAH,
            AYAH,
            kinds_checks.with_tashkeel,
            "quick",
        )
        warsh = evaluate(
            VOWEL_ERROR,
            SURAH,
            AYAH,
            AYAH,
            kinds_checks.with_warsh,
            "warsh",
        )
        self.assertEqual(checked["words"], warsh["words"])
        self.assertEqual(checked["score"], warsh["score"])
        self.assertEqual(warsh["model"], "warsh")


if __name__ == "__main__":
    unittest.main()
