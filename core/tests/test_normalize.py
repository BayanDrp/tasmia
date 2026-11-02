"""Tests for tasmia_core.normalize."""

import unittest

from tasmia_core.normalize import (
    collapse_repetition,
    display_tokens,
    display_word,
    normalize,
    normalize_text,
    normalize_word,
    strip_tashkeel,
    tashkeel_pattern,
    weak_letter_key,
    word_match,
)


class StripTashkeelTests(unittest.TestCase):
    def test_removes_common_tashkeel(self):
        self.assertEqual(strip_tashkeel("ٱلْحَمْدُ"), "ٱلحمد")

    def test_removes_superscript_alef(self):
        self.assertEqual(strip_tashkeel("ٱلرَّحْمَٰنِ"), "ٱلرحمن")

    def test_removes_quranic_waqf_mark(self):
        self.assertEqual(strip_tashkeel("قُلْ ۖ"), "قل ")

    def test_removes_end_of_ayah_and_rub_el_hizb(self):
        self.assertEqual(strip_tashkeel("قُلْ\u06DD\u06DE"), "قل")

    def test_removes_extended_b_mark(self):
        self.assertEqual(strip_tashkeel("قُلْ\u0898"), "قل")

    def test_removes_extended_a_mark(self):
        self.assertEqual(strip_tashkeel("قُلْ\u08CA"), "قل")

    def test_removes_extended_c_mark(self):
        self.assertEqual(strip_tashkeel("قُلْ\U00010EFD"), "قل")

    def test_keeps_letters_and_spaces(self):
        self.assertEqual(strip_tashkeel("قُلْ هُوَ"), "قل هو")


class TashkeelPatternTests(unittest.TestCase):
    def test_keeps_short_vowels(self):
        self.assertEqual(tashkeel_pattern("هُوَ"), "\u064F\u064E")

    def test_keeps_tanween(self):
        self.assertEqual(tashkeel_pattern("كِتَابٌ"), "\u0650\u064E\u064C")

    def test_keeps_sukun(self):
        self.assertEqual(tashkeel_pattern("مِنْ"), "\u0650\u0652")

    def test_drops_shadda(self):
        self.assertEqual(tashkeel_pattern("رَبِّ"), "\u064E\u0650")

    def test_drops_quranic_marks(self):
        self.assertEqual(tashkeel_pattern("قُلْ ۖ"), "\u064F\u0652")

    def test_warsh_and_hafs_orthography_match(self):
        self.assertEqual(
            tashkeel_pattern("اَ۬لذِےٓ"),
            tashkeel_pattern("الَّذِي"),
        )

    def test_missing_final_vowel_differs(self):
        self.assertNotEqual(
            tashkeel_pattern("صَدْرَكَ"),
            tashkeel_pattern("صَدْرَك"),
        )

    def test_empty_word(self):
        self.assertEqual(tashkeel_pattern(""), "")


class NormalizeWordTests(unittest.TestCase):
    def test_unifies_alef_forms(self):
        self.assertEqual(normalize_word("أَحَدٌ"), "احد")
        self.assertEqual(normalize_word("إِلَٰه"), "الاه")
        self.assertEqual(normalize_word("آمَنَ"), "امن")
        self.assertEqual(normalize_word("ٱلْحَمْدُ"), "الحمد")
        self.assertEqual(normalize_word("ٲحَد"), "احد")
        self.assertEqual(normalize_word("ٳحَد"), "احد")

    def test_madd_superscript_alef_becomes_alef(self):
        self.assertEqual(normalize_word("ٱلرَّحْمَٰنِ"), "الرحمان")
        self.assertEqual(normalize_word("ٱلْعَٰلَمِينَ"), "العالمين")
        self.assertEqual(normalize_word("ٱلصِّرَٰطَ"), "الصراط")

    def test_maps_warsh_yeh_barree(self):
        self.assertEqual(normalize_word("اَ۬لذِےٓ"), "الذي")
        self.assertEqual(normalize_word("فِے"), "في")

    def test_unifies_ya_and_ta_marbuta(self):
        self.assertEqual(normalize_word("مُوسَى"), "موسي")
        self.assertEqual(normalize_word("رَحْمَةٌ"), "رحمه")

    def test_unifies_hamza_carriers(self):
        self.assertEqual(normalize_word("مُؤْمِنٌ"), "مومن")
        self.assertEqual(normalize_word("شَيْءٌ"), "شي")
        self.assertEqual(normalize_word("ٴ"), "")

    def test_removes_tatweel(self):
        self.assertEqual(normalize_word("مـــد"), "مد")

    def test_removes_punctuation(self):
        self.assertEqual(normalize_word("قُلْ،"), "قل")
        self.assertEqual(normalize_word("قُلْ!"), "قل")

    def test_removes_bidi_control(self):
        self.assertEqual(normalize_word("قُلْ\u200f"), "قل")

    def test_removes_warsh_marks_for_matching(self):
        self.assertEqual(normalize_word("اِ۬لْحَمْدُ"), "الحمد")
        self.assertEqual(normalize_word("اِ۪غْفِرْ"), "اغفر")
        self.assertEqual(normalize_word("بِهِۦ"), "به")

    def test_converts_arabic_digits(self):
        self.assertEqual(normalize_word("١٢٣"), "123")
        self.assertEqual(normalize_word("۱۲۳"), "123")

    def test_maps_common_persian_letters(self):
        self.assertEqual(normalize_word("کتاب"), "كتاب")
        self.assertEqual(normalize_word("ی"), "ي")
        self.assertEqual(normalize_word("ہ"), "ه")

    def test_empty_and_punctuation_only(self):
        self.assertEqual(normalize_word(""), "")
        self.assertEqual(normalize_word("..."), "")

    def test_is_idempotent(self):
        word = normalize_word("ٱلْحَمْدُ")
        self.assertEqual(normalize_word(word), word)


class NormalizeTextTests(unittest.TestCase):
    def test_normalizes_a_full_phrase(self):
        self.assertEqual(
            normalize_text("بِسْمِ ٱللَّهِ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"),
            "بسم الله الرحمان الرحيم",
        )

    def test_collapses_spaces_and_removes_punctuation(self):
        self.assertEqual(
            normalize_text("  قُلْ،   هُوَ  ٱللَّهُ  "),
            "قل هو الله",
        )

    def test_preserves_word_order(self):
        self.assertEqual(
            normalize_text("قُلْ هُوَ ٱللَّهُ أَحَدٌ"),
            "قل هو الله احد",
        )

    def test_empty_input(self):
        self.assertEqual(normalize_text(""), "")
        self.assertEqual(normalize_text("   "), "")
        self.assertEqual(normalize_text("!!!"), "")

    def test_is_idempotent(self):
        phrase = normalize_text("ٱلْحَمْدُ لِلَّهِ رَبِّ ٱلْعَٰلَمِينَ")
        self.assertEqual(normalize_text(phrase), phrase)

    def test_alias(self):
        phrase = "قُلْ هُوَ ٱللَّهُ أَحَدٌ"
        self.assertEqual(normalize(phrase), normalize_text(phrase))


class WeakLetterKeyTests(unittest.TestCase):
    def test_ignores_alef_waw_ya(self):
        self.assertEqual(weak_letter_key("الْعَٰلَمِينَ"), "لعلمن")
        self.assertEqual(weak_letter_key("العالمين"), "لعلمن")
        self.assertEqual(weak_letter_key("الصِّرَٰطَ"), "لصرط")
        self.assertEqual(weak_letter_key("الصراط"), "لصرط")
        self.assertEqual(weak_letter_key("السَّمَٰوَٰتِ"), "لسمت")
        self.assertEqual(weak_letter_key("السماوات"), "لسمت")
        self.assertEqual(weak_letter_key("الرَّحْمَٰنِ"), "لرحمن")
        self.assertEqual(weak_letter_key("الرحمان"), "لرحمن")

    def test_keeps_a_key_for_weak_only_words(self):
        self.assertEqual(weak_letter_key("و"), "و")
        self.assertEqual(weak_letter_key("يا"), "يا")

    def test_punctuation_only_has_empty_key(self):
        self.assertEqual(weak_letter_key("..."), "")
        self.assertEqual(weak_letter_key(""), "")


class WordMatchTests(unittest.TestCase):
    def test_exact_match(self):
        self.assertEqual(word_match("قُلْ", "قل"), "exact")
        self.assertEqual(word_match("الْحَمْدُ", "الحمد"), "exact")

    def test_warsh_yeh_barree_matches_ya(self):
        self.assertEqual(word_match("اَ۬لذِےٓ", "الذي"), "exact")
        self.assertEqual(word_match("فِے", "في"), "exact")

    def test_madd_words_match_exactly(self):
        self.assertEqual(word_match("الْعَٰلَمِينَ", "العالمين"), "exact")
        self.assertEqual(word_match("الصِّرَٰطَ", "الصراط"), "exact")
        self.assertEqual(word_match("الرَّحْمَٰنِ", "الرحمان"), "exact")
        self.assertEqual(word_match("السَّمَٰوَٰتِ", "السماوات"), "exact")

    def test_weak_match(self):
        # Same letters once weak letters are dropped, but the madd alef was
        # omitted: a weak (mispronounced) match, not exact.
        self.assertEqual(word_match("الرَّحْمَٰنِ", "الرحمن"), "weak")
        self.assertEqual(word_match("قَالَ", "قل"), "weak")

    def test_mismatch(self):
        self.assertEqual(word_match("قُلْ", "كل"), "mismatch")
        self.assertEqual(word_match("", "قل"), "mismatch")
        self.assertEqual(word_match("...", "..."), "mismatch")


class DisplayWordTests(unittest.TestCase):
    def test_keeps_tashkeel_and_quranic_alef(self):
        self.assertEqual(display_word("ٱلْحَمْدُ"), "ٱلْحَمْدُ")
        self.assertEqual(display_word("ٱلرَّحْمَٰنِ"), "ٱلرَّحْمَٰنِ")

    def test_does_not_normalize_letters(self):
        self.assertEqual(display_word("أَحَدٌ"), "أَحَدٌ")
        self.assertEqual(display_word("مُوسَى"), "مُوسَى")
        self.assertEqual(display_word("رَحْمَةٌ"), "رَحْمَةٌ")

    def test_removes_punctuation(self):
        self.assertEqual(display_word("قُلْ،"), "قُلْ")
        self.assertEqual(display_word("قُلْ!"), "قُلْ")

    def test_removes_waqf_marks(self):
        self.assertEqual(display_word("قُلْ ۖ"), "قُلْ")
        self.assertEqual(display_word("قُلْ\u06DD\u06DE"), "قُلْ")
        self.assertEqual(display_word("\u0898"), "")
        self.assertEqual(display_word("\u08CA"), "")
        self.assertEqual(display_word("\U00010EFD"), "")

    def test_keeps_warsh_marks(self):
        self.assertEqual(display_word("اِ۬لْحَمْدُ"), "اِ۬لْحَمْدُ")
        self.assertEqual(display_word("اِ۪غْفِرْ"), "اِ۪غْفِرْ")
        self.assertEqual(display_word("بِهِۦ"), "بِهِۦ")
        self.assertEqual(display_word("قُلْ\u06E5"), "قُلْ\u06E5")

    def test_removes_pause_marks_but_keeps_warsh_marks(self):
        self.assertEqual(display_word("اِ۬لْحَمْدُۖ"), "اِ۬لْحَمْدُ")
        self.assertEqual(display_word("قُلْ ۩"), "قُلْ")
        self.assertEqual(display_word("مِنۢ"), "مِن")
        self.assertEqual(display_word("قُلْ\u06ED"), "قُلْ")

    def test_removes_tatweel(self):
        self.assertEqual(display_word("مـــد"), "مد")

    def test_removes_bidi_control(self):
        self.assertEqual(display_word("قُلْ\u200f"), "قُلْ")

    def test_empty_and_marks_only(self):
        self.assertEqual(display_word(""), "")
        self.assertEqual(display_word("..."), "")
        self.assertEqual(display_word("ۖ"), "")


class DisplayTokensTests(unittest.TestCase):
    def test_returns_display_words(self):
        self.assertEqual(
            display_tokens("قُلْ هُوَ ٱللَّهُ أَحَدٌ ۖ"),
            ["قُلْ", "هُوَ", "ٱللَّهُ", "أَحَدٌ"],
        )

    def test_drops_standalone_marks(self):
        self.assertEqual(
            display_tokens("بِسْمِ ٱللَّهِ ۝ ٱلرَّحْمَٰنِ ٱلرَّحِيمِ"),
            ["بِسْمِ", "ٱللَّهِ", "ٱلرَّحْمَٰنِ", "ٱلرَّحِيمِ"],
        )

    def test_handles_punctuation_and_spaces(self):
        self.assertEqual(
            display_tokens("  قُلْ،   هُوَ  ٱللَّهُ  "),
            ["قُلْ", "هُوَ", "ٱللَّهُ"],
        )

    def test_preserves_word_order(self):
        words = ["قُلْ", "هُوَ", "ٱللَّهُ", "أَحَدٌ"]
        self.assertEqual(display_tokens(" ".join(words)), words)

    def test_empty_input(self):
        self.assertEqual(display_tokens(""), [])
        self.assertEqual(display_tokens("   "), [])
        self.assertEqual(display_tokens("ۖ ۝"), [])


class CollapseRepetitionTests(unittest.TestCase):
    def test_collapses_hallucination_loop(self):
        loop = "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا " + "او " * 200
        result = collapse_repetition(loop.strip())
        self.assertEqual(result.count("او"), 10)

    def test_keeps_doubles_and_triples(self):
        self.assertEqual(collapse_repetition("يُسْرًا يُسْرًا"), "يُسْرًا يُسْرًا")
        self.assertEqual(collapse_repetition("قل قل قل"), "قل قل قل")

    def test_normal_text_untouched(self):
        ayah = "قُلْ هُوَ ٱللَّهُ أَحَدٌ ٱللَّهُ ٱلصَّمَدُ"
        self.assertEqual(collapse_repetition(ayah), ayah)

    def test_repeated_ayah_survives(self):
        # A reciter practising an ayah twice must keep both copies.
        twice = "فَإِنَّ مَعَ الْعُسْرِ يُسْرًا فَإِنَّ مَعَ الْعُسْرِ يُسْرًا"
        self.assertEqual(collapse_repetition(twice), twice)

    def test_empty_input(self):
        self.assertEqual(collapse_repetition(""), "")
        self.assertEqual(collapse_repetition("   "), "")


if __name__ == "__main__":
    unittest.main()
