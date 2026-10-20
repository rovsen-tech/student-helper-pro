import unittest

from speech_preparation import prepare_speech_text


class PrepareSpeechTextTests(unittest.TestCase):
    def prepare(self, text, **overrides):
        options = {
            "lang": "az",
            "subject": "Riyaziyyat",
            "topic": "Ədədlər",
        }
        options.update(overrides)
        return prepare_speech_text(text, **options)

    def test_ordinary_azerbaijani_prose_is_unchanged(self):
        text = "Bu gün maraqlı bir mövzu öyrənəcəyik."
        self.assertEqual(self.prepare(text), text)

    def test_multiplication_in_math_context_is_prepared(self):
        self.assertEqual(self.prepare("2 × 5"), "2 vur 5")

    def test_division_in_math_context_is_prepared(self):
        self.assertEqual(self.prepare("10 ÷ 2"), "10 böl 2")

    def test_operators_are_unchanged_without_math_topic(self):
        text = "2 × 5 və 10 ÷ 2"
        self.assertEqual(self.prepare(text, topic="Mövzu"), text)

    def test_azerbaijani_identifier_around_operator_is_preserved(self):
        text = "Ədəd2 × 5ədəd"
        self.assertEqual(self.prepare(text), text)

    def test_lesson_identifier_adjacent_to_operator_is_preserved(self):
        text = "lesson_05×2"
        self.assertEqual(self.prepare(text), text)

    def test_ordinary_multiplication_after_punctuation_is_prepared(self):
        self.assertEqual(self.prepare("Əli: 2 × 5!"), "Əli: 2 vur 5!")

    def test_only_confirmed_three_fourths_is_converted(self):
        options = {
            "topic": "Adi kəsrlər",
            "fraction_confirmed": True,
        }
        self.assertEqual(self.prepare("3/4", **options), "dörddə üç")
        self.assertEqual(self.prepare("2/3", **options), "2/3")

    def test_unconfirmed_fraction_is_unchanged(self):
        text = "3/4"
        self.assertEqual(self.prepare(text, topic="Adi kəsrlər"), text)

    def test_fraction_outside_fraction_topic_is_unchanged(self):
        text = "3/4"
        self.assertEqual(
            self.prepare(text, topic="Ədədlər", fraction_confirmed=True),
            text,
        )

    def test_same_line_spaced_fraction_is_converted(self):
        self.assertEqual(
            self.prepare(
                "3 / 4",
                topic="Adi kəsrlər",
                fraction_confirmed=True,
            ),
            "dörddə üç",
        )

    def test_fraction_split_across_lines_is_not_joined(self):
        text = "3\n/\n4"
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            text,
        )

    def test_compact_date_is_not_converted_as_fraction(self):
        text = "3/4/2025"
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            text,
        )

    def test_spaced_date_is_not_partially_converted_as_fraction(self):
        text = "3 / 4 / 2025"
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            text,
        )

    def test_inline_code_is_preserved(self):
        text = "`2 × 5` and `3/4`"
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            text,
        )

    def test_closed_fenced_code_is_preserved(self):
        text = "Before ```\n2 × 5 and 3/4\n``` after 2 × 5"
        expected = "Before ```\n2 × 5 and 3/4\n``` after 2 vur 5"
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            expected,
        )

    def test_unclosed_fenced_code_is_preserved_to_end_of_text(self):
        text = "Before 2 × 5\n```\ninside 10 ÷ 2 and 3/4"
        expected = "Before 2 vur 5\n```\ninside 10 ÷ 2 and 3/4"
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            expected,
        )

    def test_url_contents_are_preserved(self):
        text = "https://example.test/2×5"
        self.assertEqual(self.prepare(text), text)

    def test_url_punctuation_and_following_fraction_are_preserved_in_order(self):
        text = "https://example.test/2×5, sonra 3/4."
        expected = "https://example.test/2×5, sonra dörddə üç."
        self.assertEqual(
            self.prepare(text, topic="Adi kəsrlər", fraction_confirmed=True),
            expected,
        )

    def test_email_version_and_identifiers_are_preserved(self):
        text = "teacher+test@example.test v1.2.3 lesson_05 item42"
        self.assertEqual(self.prepare(text), text)

    def test_dates_times_decimals_and_negative_numbers_are_preserved(self):
        text = "16.10.2026; 09:30; 3,14; -3"
        self.assertEqual(self.prepare(text), text)

    def test_operators_split_across_lines_are_not_joined(self):
        for text in ("2\n×\n5", "10\n÷\n2"):
            with self.subTest(text=text):
                self.assertEqual(self.prepare(text), text)

    def test_lowercase_x_equation_is_prepared_in_algebra_topic(self):
        self.assertEqual(
            self.prepare("x = 5", topic="Sadə tənliklər"),
            "x bərabərdir 5",
        )

    def test_uppercase_x_and_other_equations_are_preserved(self):
        for text in ("X = 5", "y = 5", "x = 6"):
            with self.subTest(text=text):
                self.assertEqual(
                    self.prepare(text, topic="Sadə tənliklər"),
                    text,
                )

    def test_equation_inside_prose_is_preserved(self):
        text = "Nümunədə x = 5 götürülür."
        self.assertEqual(self.prepare(text, topic="Tənliklər"), text)

    def test_percent_in_ordinary_sentence_is_preserved(self):
        text = "Məhsula 25% endirim edildi."
        self.assertEqual(self.prepare(text, topic="Faizlər"), text)

    def test_standalone_percent_is_prepared_in_percent_topic(self):
        self.assertEqual(self.prepare("25%", topic="Faizlər"), "25 faiz")

    def test_percent_is_preserved_outside_percent_topic(self):
        self.assertEqual(self.prepare("25%", topic="Ədədlər"), "25%")

    def test_turkish_and_english_text_are_unchanged(self):
        text = "2 × 5; 10 ÷ 2; 25%"
        for lang in ("tr", "en"):
            with self.subTest(lang=lang):
                self.assertEqual(
                    self.prepare(text, lang=lang, topic="Faizlər"),
                    text,
                )

    def test_non_math_subject_is_unchanged(self):
        text = "2 × 5"
        self.assertEqual(
            self.prepare(text, subject="Azərbaycan dili"),
            text,
        )

    def test_azerbaijani_letters_and_punctuation_are_preserved(self):
        text = "Əli, Ülkər və Şəfəq: 2 × 5!"
        self.assertEqual(
            self.prepare(text),
            "Əli, Ülkər və Şəfəq: 2 vur 5!",
        )

    def test_empty_string_is_unchanged(self):
        self.assertEqual(self.prepare(""), "")

    def test_none_is_returned_unchanged(self):
        self.assertIsNone(self.prepare(None))

    def test_non_string_input_is_returned_unchanged(self):
        value = ["2 × 5"]
        self.assertIs(self.prepare(value), value)

    def test_reprocessing_prepared_text_is_stable(self):
        first = self.prepare("2 × 5 və 10 ÷ 2")
        self.assertEqual(self.prepare(first), first)

    def test_preparation_does_not_mutate_display_text(self):
        display_text = "3/4"
        speech_text = self.prepare(
            display_text,
            topic="Adi kəsrlər",
            fraction_confirmed=True,
        )
        self.assertEqual(display_text, "3/4")
        self.assertEqual(speech_text, "dörddə üç")


if __name__ == "__main__":
    unittest.main()
