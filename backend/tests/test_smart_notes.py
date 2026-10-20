import os
import sys
import time
import unittest

# Həm repo kökündən, həm də backend/ qovluğundan işə salmaq üçün.
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from smart_notes import (  # noqa: E402
    _AZ_MARKER_RE,
    clean_markdown_line,
    generate_smart_notes,
    has_marker,
    split_sentences,
)


def assistant(text):
    return {"role": "assistant", "content": text}


class MarkerTests(unittest.TestCase):
    def test_azerbaijani_suffixed_markers_match(self):
        for word in ("imtahanda", "düsturu", "qaydanı", "vacibdir", "İmtahanda", "Diqqətli", "qeydlər"):
            with self.subTest(word=word):
                self.assertTrue(has_marker(f"Bu {word} lazımdır."))

    def test_regex_matches_full_suffixed_word(self):
        self.assertEqual(_AZ_MARKER_RE.search("qaydanı yadda saxla").group(0), "qaydanı")

    def test_marker_not_matched_inside_other_word(self):
        self.assertFalse(has_marker("Birqeydsiz söz."))

    def test_english_markers_use_strict_boundary(self):
        self.assertTrue(has_marker("This is on the exam."))
        self.assertTrue(has_marker("A short test today."))
        self.assertFalse(has_marker("The examples are testing ideas."))


class MarkdownTests(unittest.TestCase):
    def test_bold_and_list_prefixes_are_stripped(self):
        self.assertEqual(clean_markdown_line("- **Qayda:** Böl"), "Qayda: Böl")
        self.assertEqual(clean_markdown_line("# Başlıq"), "Başlıq")
        self.assertEqual(clean_markdown_line("1. Birinci addım"), "Birinci addım")
        self.assertEqual(clean_markdown_line("* __vacib__ fikir"), "vacib fikir")

    def test_math_is_untouched(self):
        for text in ("−3/4 mənfi kəsrdir", "-3/4 kəsrdir", "3/4 kəsrdir", "0.5 onluqdur", "2 < 5 və 7 > 3"):
            with self.subTest(text=text):
                self.assertEqual(clean_markdown_line(text), text)

    def test_number_alone_is_not_a_sentence(self):
        self.assertEqual(split_sentences("1."), [])
        self.assertEqual(split_sentences("1.\n2.\nKəsr hissədir."), ["Kəsr hissədir."])

    def test_decimal_does_not_split_sentence(self):
        self.assertEqual(split_sentences("Yarım 0.5 deməkdir. Sonra davam."),
                         ["Yarım 0.5 deməkdir.", "Sonra davam."])


class GenerateNotesTests(unittest.TestCase):
    def test_bold_definition_is_extracted(self):
        notes = generate_smart_notes([assistant("**Tərif:** Kəsr — hissə")], topic="Adi kəsrlər")
        self.assertIn("Kəsr — hissə", notes["definitions"])

    def test_list_prefixed_rule_is_extracted(self):
        notes = generate_smart_notes([assistant("- Qayda: Surəti və məxrəci eyni ədədə vur.")])
        self.assertIn("Surəti və məxrəci eyni ədədə vur.", notes["rules"])

    def test_definition_verb_and_formula(self):
        notes = generate_smart_notes([assistant(
            "Üstdəki ədədə surət deyilir.\nDüstur: S = a × b\nNümunə: 3 + 2 = 5 olur.")])
        self.assertIn("Üstdəki ədədə surət deyilir.", notes["definitions"])
        self.assertIn("S = a × b", notes["formulas"])
        self.assertIn("Nümunə: 3 + 2 = 5 olur.", notes["formulas"])

    def test_exam_tips_with_suffix(self):
        notes = generate_smart_notes([assistant("İmtahanda bu sual tez-tez düşür.")])
        self.assertEqual(notes["exam_tips"], ["İmtahanda bu sual tez-tez düşür."])

    def test_non_assistant_roles_are_ignored(self):
        conv = [
            {"role": "user", "content": "Tərif: Şagirdin uydurması."},
            {"role": "system", "content": "Qayda: gizli."},
            assistant("Tərif: Kəsr bütövün hissəsidir."),
        ]
        notes = generate_smart_notes(conv)
        self.assertEqual(notes["definitions"], ["Kəsr bütövün hissəsidir."])
        self.assertEqual(notes["rules"], [])
        self.assertEqual(notes["source_message_count"], 1)
        joined = " ".join(sum((v for v in notes.values() if isinstance(v, list)), []))
        self.assertNotIn("uydurması", joined)
        self.assertNotIn("gizli", joined)

    def test_long_whitespace_is_fast(self):
        content = "Kəsr" + " " * 20000 + "hissədir." + "\n" * 2000 + "\t" * 5000
        conv = [assistant(content)]
        start = time.perf_counter()
        generate_smart_notes(conv)
        self.assertLess(time.perf_counter() - start, 0.1)

    def test_redos_style_inputs_are_fast(self):
        payloads = ["Tərif:" + " " * 20000 + "x", "Qayda:" + " \t" * 10000 + "!", "a" + " =" * 4000]
        start = time.perf_counter()
        for p in payloads:
            generate_smart_notes([assistant(p)])
        self.assertLess(time.perf_counter() - start, 0.1)

    def test_empty_and_invalid_input(self):
        for conv in (None, [], [{"role": "assistant", "content": None}], [{"role": "assistant"}]):
            with self.subTest(conv=conv):
                notes = generate_smart_notes(conv)
                self.assertEqual(notes["definitions"], [])
                self.assertEqual(notes["key_concepts"], [])
                self.assertEqual(notes["vocabulary"], [])

    def test_unknown_lang_defaults_to_az(self):
        self.assertEqual(generate_smart_notes([], lang="tr")["lang"], "az")
        self.assertEqual(generate_smart_notes([], lang="en")["lang"], "en")

    def test_key_concepts_and_summary(self):
        conv = [assistant("Kəsr bütövün hissəsidir. Kəsr iki ədəddən ibarətdir. Bu vacibdir: məxrəc sıfır ola bilməz.")]
        notes = generate_smart_notes(conv, subject="Riyaziyyat", topic="Adi kəsrlər")
        self.assertEqual(notes["key_concepts"][0], "Adi kəsrlər")
        self.assertIn("kəsr", notes["key_concepts"])
        self.assertEqual(notes["summary"][0], "Bu vacibdir: məxrəc sıfır ola bilməz.")
        self.assertEqual(notes["title"], "Adi kəsrlər")

    def test_only_last_100_messages_used(self):
        conv = [assistant(f"Tərif: köhnə {i}.") for i in range(50)] + [assistant("Salam.")] * 100
        self.assertEqual(generate_smart_notes(conv)["definitions"], [])

    def test_exam_mode_raises_tip_limit(self):
        conv = [assistant(" ".join(f"İmtahan sualı {i}." for i in range(12)))]
        self.assertEqual(len(generate_smart_notes(conv)["exam_tips"]), 5)
        self.assertEqual(len(generate_smart_notes(conv, exam_mode=True)["exam_tips"]), 10)


class ServerModelTests(unittest.TestCase):
    """server.py-nin asılılıqları (Mongo, emergentintegrations) yoxdursa ötürülür."""

    @classmethod
    def setUpClass(cls):
        os.environ.setdefault("MONGO_URL", "mongodb://localhost:27017")
        os.environ.setdefault("DB_NAME", "test_db")
        try:
            import server  # noqa: F401
        except Exception as exc:  # pragma: no cover
            raise unittest.SkipTest(f"server import edilmədi: {exc}")
        cls.server = server

    def test_lang_normalized_and_content_limited(self):
        from pydantic import ValidationError
        req = self.server.SmartNotesRequest(lang="tr", conversation=[])
        self.assertEqual(req.lang, "az")
        with self.assertRaises(ValidationError):
            self.server.SmartNotesMessage(role="assistant", content="x" * 8001)

    def test_endpoint_does_not_touch_db(self):
        import asyncio
        req = self.server.SmartNotesRequest(conversation=[{"role": "assistant", "content": "Tərif: Kəsr hissədir."}])
        original = self.server.db
        self.server.db = None  # hər hansı DB çağırışı xəta verərdi
        try:
            res = self.server.generate_notes(req)
            if asyncio.iscoroutine(res):
                res = asyncio.run(res)
        finally:
            self.server.db = original
        self.assertEqual(res["definitions"], ["Kəsr hissədir."])


if __name__ == "__main__":
    unittest.main()
