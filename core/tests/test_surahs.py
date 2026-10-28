"""Tests for tasmia_core.surahs."""

from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from tasmia_core.normalize import normalize_word
from tasmia_core.surahs import (
    DEFAULT_QURAN_PATH,
    QuranDataError,
    QuranRepository,
)


REPO: QuranRepository


def setUpModule() -> None:
    global REPO
    REPO = QuranRepository.load()


def _minimal_surah(
    surah_id: int = 1,
    *,
    ayah_number: int = 1,
    total_verses: int = 1,
) -> dict:
    return {
        "id": surah_id,
        "name": "سورة اختبار",
        "full_name": "سورة اختبار",
        "total_verses": total_verses,
        "basmala_before_surah": True,
        "ayahs": [
            {
                "number": ayah_number,
                "text": "بِسْمِ",
                "juz": 1,
                "hizb": 1,
                "rub": 1,
                "page": 1,
                "number_in_hafs": [1],
            }
        ],
    }


class LoadTests(unittest.TestCase):
    def test_default_path_exists(self):
        self.assertTrue(DEFAULT_QURAN_PATH.is_file())

    def test_counts(self):
        self.assertEqual(len(REPO.list_surahs()), 114)
        self.assertEqual(len(REPO.list_hizbs()), 60)
        self.assertEqual(
            sum(surah.total_verses for surah in REPO.list_surahs()),
            6214,
        )

    def test_basmala_is_loaded(self):
        self.assertTrue(REPO.basmala.startswith("بِسْمِ"))

    def test_missing_file(self):
        with self.assertRaises(FileNotFoundError):
            QuranRepository.load("/tmp/tasmia-missing-quran.json")

    def test_invalid_json_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "quran.json"
            path.write_text("{", encoding="utf-8")
            with self.assertRaises(QuranDataError):
                QuranRepository.load(path)


class SurahTests(unittest.TestCase):
    def test_first_surah(self):
        surah = REPO.get_surah(1)
        self.assertEqual(surah.id, 1)
        self.assertEqual(surah.name, "الفاتحة")
        self.assertEqual(surah.total_verses, 7)
        self.assertEqual(len(surah.ayahs), 7)
        self.assertTrue(surah.basmala_before_surah)

    def test_tawbah_has_no_basmala(self):
        self.assertFalse(REPO.get_surah(9).basmala_before_surah)

    def test_last_surah(self):
        surah = REPO.get_surah(114)
        self.assertEqual(surah.name, "الناس")
        self.assertEqual(surah.total_verses, 6)

    def test_get_ayah(self):
        ayah = REPO.get_ayah(1, 1)
        self.assertEqual(ayah.number, 1)
        self.assertEqual(ayah.juz, 1)
        self.assertEqual(ayah.hizb, 1)
        self.assertEqual(ayah.rub, 1)
        self.assertEqual(ayah.page, 1)
        self.assertEqual(ayah.number_in_hafs, (1, 2))

    def test_invalid_surah(self):
        with self.assertRaises(ValueError):
            REPO.get_surah(0)
        with self.assertRaises(ValueError):
            REPO.get_surah(115)

    def test_invalid_ayah(self):
        with self.assertRaises(ValueError):
            REPO.get_ayah(1, 0)
        with self.assertRaises(ValueError):
            REPO.get_ayah(1, 8)
        with self.assertRaises(ValueError):
            REPO.get_ayah(0, 1)


class HizbTests(unittest.TestCase):
    def test_first_hizb(self):
        hizb = REPO.get_hizb(1)
        self.assertEqual(hizb.number, 1)
        self.assertEqual(hizb.juz, 1)
        self.assertEqual(hizb.start, (1, 1))
        self.assertEqual(hizb.end, (2, 74))

    def test_last_hizb(self):
        hizb = REPO.get_hizb(60)
        self.assertEqual(hizb.number, 60)
        self.assertEqual(hizb.juz, 30)
        self.assertEqual(hizb.start, (87, 1))
        self.assertEqual(hizb.end, (114, 6))

    def test_all_hizbs(self):
        for number in range(1, 61):
            hizb = REPO.get_hizb(number)
            self.assertEqual(hizb.number, number)
            self.assertEqual(REPO.get_ayah(*hizb.start).hizb, number)
            self.assertEqual(REPO.get_ayah(*hizb.end).hizb, number)

    def test_invalid_hizb(self):
        with self.assertRaises(ValueError):
            REPO.get_hizb(0)
        with self.assertRaises(ValueError):
            REPO.get_hizb(61)


class ExpectedWordsTests(unittest.TestCase):
    def test_fatiha_first_ayah_with_basmala(self):
        words = REPO.expected_words(1, 1, 1)
        self.assertEqual(len(words), 8)
        self.assertEqual([word.ayah for word in words], [0, 0, 0, 0, 1, 1, 1, 1])
        self.assertEqual(
            [word.index for word in words if word.ayah == 0],
            [1, 2, 3, 4],
        )
        self.assertEqual(words[0].text, "بِسْمِ")
        self.assertEqual(words[4].text, "اِ۬لْحَمْدُ")
        self.assertEqual(words[4].normalized, "الحمد")
        self.assertEqual(words[7].normalized, "العالمين")

    def test_fatiha_first_ayah_without_basmala(self):
        words = REPO.expected_words(1, 1, 1, include_basmala=False)
        self.assertEqual(len(words), 4)
        self.assertTrue(all(word.ayah == 1 for word in words))
        self.assertEqual(words[0].text, "اِ۬لْحَمْدُ")
        self.assertEqual(words[0].index, 1)

    def test_starting_after_ayah_one_skips_basmala(self):
        words = REPO.expected_words(1, 2, 2)
        self.assertTrue(all(word.ayah == 2 for word in words))
        self.assertEqual(normalize_word(words[0].text), "الرحمان")

    def test_tawbah_has_no_basmala(self):
        words = REPO.expected_words(9, 1, 1)
        self.assertTrue(all(word.ayah == 1 for word in words))
        self.assertEqual(words[0].text, "بَرَآءَةٞ")

    def test_naba_has_basmala(self):
        words = REPO.expected_words(78, 1, 1)
        self.assertEqual(len(words), 6)
        self.assertEqual([word.ayah for word in words], [0, 0, 0, 0, 1, 1])
        self.assertEqual(normalize_word(words[4].text), "عم")

    def test_ayah_to_none_returns_rest_of_surah(self):
        words = REPO.expected_words(1, 7)
        self.assertTrue(all(word.ayah == 7 for word in words))

    def test_indexes_restart_for_each_ayah(self):
        words = REPO.expected_words(1, 1, 3)
        for ayah_number in (1, 2, 3):
            indexes = [word.index for word in words if word.ayah == ayah_number]
            self.assertEqual(indexes, list(range(1, len(indexes) + 1)))

    def test_normalized_matches_normalize_word(self):
        for word in REPO.expected_words(1, 1, 2):
            self.assertEqual(word.normalized, normalize_word(word.text))

    def test_invalid_surah(self):
        with self.assertRaises(ValueError):
            REPO.expected_words(0, 1, 1)
        with self.assertRaises(ValueError):
            REPO.expected_words(115, 1, 1)

    def test_invalid_range(self):
        for args in [
            (1, 0, 1),
            (1, 2, 1),
            (1, 1, 8),
            (1, 1, 999),
        ]:
            with self.subTest(args=args):
                with self.assertRaises(ValueError):
                    REPO.expected_words(*args)

    def test_non_integer_range(self):
        with self.assertRaises(ValueError):
            REPO.expected_words(1, 1.5, 2)  # type: ignore[arg-type]
        with self.assertRaises(ValueError):
            REPO.expected_words(1, True, 2)


class ValidationTests(unittest.TestCase):
    def test_missing_basmala(self):
        with self.assertRaises(QuranDataError):
            QuranRepository.from_dict({"surahs": [], "hizbs": []})

    def test_empty_surahs(self):
        with self.assertRaises(QuranDataError):
            QuranRepository.from_dict(
                {"basmala": "بِسْمِ", "surahs": [], "hizbs": []}
            )

    def test_duplicate_surah_ids(self):
        data = {
            "basmala": "بِسْمِ",
            "surahs": [_minimal_surah(1), _minimal_surah(1)],
            "hizbs": [],
        }
        with self.assertRaises(QuranDataError):
            QuranRepository.from_dict(data)

    def test_bad_ayah_number(self):
        data = {
            "basmala": "بِسْمِ",
            "surahs": [_minimal_surah(ayah_number=2)],
            "hizbs": [],
        }
        with self.assertRaises(QuranDataError):
            QuranRepository.from_dict(data)

    def test_total_verses_mismatch(self):
        data = {
            "basmala": "بِسْمِ",
            "surahs": [_minimal_surah(total_verses=2)],
            "hizbs": [],
        }
        with self.assertRaises(QuranDataError):
            QuranRepository.from_dict(data)

    def test_basmala_flag_must_be_bool(self):
        surah = _minimal_surah()
        surah["basmala_before_surah"] = "yes"
        data = {"basmala": "بِسْمِ", "surahs": [surah], "hizbs": []}
        with self.assertRaises(QuranDataError):
            QuranRepository.from_dict(data)


if __name__ == "__main__":
    unittest.main()