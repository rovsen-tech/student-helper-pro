"""Pure compatibility tests for legacy textbook-shaped dictionaries."""
import copy
import unittest

from pydantic import ValidationError

from learning_adapters import (
    AdaptedLegacyRecord,
    adapt_legacy_lesson,
    adapt_legacy_section,
    adapt_legacy_structured_content,
    adapt_legacy_textbook,
    reconstruct_legacy_document,
)


def source_book():
    return {
        "id": "tb-math-5",
        "subject_id": "riyaziyyat",
        "title": "Riyaziyyat 5",
        "grade": "5",
        "edition": "2025",
        "grif": "approved",
        "provenance": "SOURCE",
        "created_at": "2025-01-01T00:00:00+00:00",
        "custom": {"labels": ["official", "az"]},
    }


def source_section():
    return {
        "id": "tb-math-5-sec-1",
        "textbook_id": "tb-math-5",
        "order": 1,
        "title": "Kəsrlər",
        "custom_section_flag": False,
    }


def source_lesson():
    return {
        "id": "tb-math-5-l1.2",
        "textbook_id": "tb-math-5",
        "section_id": "tb-math-5-sec-1",
        "order": 2,
        "number": "1.2",
        "title": "Kəsrlərin müqayisəsi",
        "page_start": 17,
        "page_end": 18,
        "content": [
            {
                "type": "explanation",
                "provenance": "SOURCE",
                "text": "Məxrəclər bərabərdirsə, surətləri müqayisə et.",
                "normalized_text": "Məxrəclər bərabərdirsə, surətləri müqayisə et.",
                "original_text": "Məxrəclər bərabərdirsə, surətləri müqayisə et.",
                "page_start": 17,
                "page_end": 18,
                "source_page": 17,
                "layout_hint": {"column": 1},
            },
            {
                "type": "worked_example",
                "provenance": "DERIVED",
                "text": "3/8 < 5/8",
                "normalized_text": "3/8 < 5/8",
                "original_text": "3/8 < 5/8",
                "page_start": 18,
                "page_end": 18,
                "source_page": 18,
            },
        ],
        "legacy_review": {"checked": False},
    }


class LegacyAdapterTests(unittest.TestCase):
    def test_actual_textbook_section_lesson_relationships_and_ids_are_preserved(self):
        textbook = adapt_legacy_textbook(source_book())
        section = adapt_legacy_section(source_section())
        lesson = adapt_legacy_lesson(source_lesson())

        self.assertEqual(textbook.contract["id"], "tb-math-5")
        self.assertEqual(textbook.contract["edition"], "2025")
        self.assertEqual(section.contract["id"], "tb-math-5-sec-1")
        self.assertEqual(section.contract["source_document_id"], textbook.contract["id"])
        self.assertEqual(section.contract["order"], 1)
        self.assertEqual(lesson.contract["id"], "tb-math-5-l1.2")
        self.assertEqual(lesson.contract["source_document_id"], textbook.contract["id"])
        self.assertEqual(lesson.contract["parent_id"], section.contract["id"])
        self.assertEqual(lesson.contract["order"], 2)
        self.assertEqual(lesson.legacy_metadata["number"], "1.2")

    def test_content_order_numbering_text_and_provenance_are_preserved(self):
        adapted = adapt_legacy_lesson(source_lesson())
        blocks = adapted.contract["content_blocks"]
        self.assertEqual([block["content_type"] for block in blocks], ["explanation", "worked_example"])
        self.assertEqual([block["provenance"] for block in blocks], ["SOURCE", "DERIVED"])
        self.assertEqual(blocks[0]["text"], "Məxrəclər bərabərdirsə, surətləri müqayisə et.")
        self.assertEqual(blocks[1]["original_text"], "3/8 < 5/8")

    def test_ambiguous_legacy_page_fields_are_preserved_not_mapped_to_pdf_pages(self):
        lesson = adapt_legacy_lesson(source_lesson())
        self.assertEqual(lesson.contract["page_refs"], [])
        self.assertEqual(lesson.legacy_metadata["page_start"], 17)
        self.assertEqual(lesson.legacy_metadata["page_end"], 18)
        self.assertEqual(lesson.legacy_metadata["content_unmapped_fields"][0]["source_page"], 17)
        self.assertEqual(lesson.contract["content_blocks"][0]["source_refs"], [])

    def test_structured_content_keeps_original_and_normalized_text_and_unknown_fields(self):
        raw = source_lesson()["content"][0]
        adapted = adapt_legacy_structured_content(raw)
        self.assertEqual(adapted.contract["content_type"], "explanation")
        self.assertEqual(adapted.contract["text"], raw["text"])
        self.assertEqual(adapted.contract["normalized_text"], raw["normalized_text"])
        self.assertEqual(adapted.contract["original_text"], raw["original_text"])
        self.assertEqual(adapted.legacy_metadata["page_start"], 17)
        self.assertEqual(adapted.legacy_metadata["layout_hint"], {"column": 1})

    def test_missing_null_and_empty_values_reconstruct_exactly(self):
        cases = [
            (adapt_legacy_textbook, {"id": "book", "title": "T"}),
            (adapt_legacy_textbook, {"id": "book", "title": "T", "grade": None, "tags": []}),
            (adapt_legacy_section, {"id": "sec", "textbook_id": "book", "title": "S"}),
            (adapt_legacy_lesson, {
                "id": "lesson", "textbook_id": "book", "section_id": "sec", "title": "L", "content": []
            }),
            (adapt_legacy_lesson, {
                "id": "lesson", "textbook_id": "book", "section_id": "sec", "title": "L",
                "page_start": None, "page_end": None, "content": [], "notes": None,
            }),
            (adapt_legacy_structured_content, {
                "type": "note", "text": "", "provenance": "SOURCE", "normalized_text": None,
            }),
        ]
        for adapt, original in cases:
            with self.subTest(original=original):
                result = adapt(original)
                self.assertEqual(reconstruct_legacy_document(result), original)
                serialized = result.model_dump(mode="json")
                self.assertEqual(reconstruct_legacy_document(serialized), original)

    def test_unknown_fields_are_separately_identified_and_exactly_reconstructed(self):
        original = source_book()
        adapted = adapt_legacy_textbook(original)
        self.assertEqual(adapted.legacy_metadata["subject_id"], "riyaziyyat")
        self.assertEqual(adapted.legacy_metadata["custom"], {"labels": ["official", "az"]})
        self.assertNotIn("custom", adapted.contract)
        self.assertEqual(reconstruct_legacy_document(adapted), original)

    def test_conversion_is_deeply_immutable_and_reconstruction_is_independent(self):
        original = source_lesson()
        before = copy.deepcopy(original)
        adapted = adapt_legacy_lesson(original)
        self.assertEqual(original, before)
        original["content"][0]["layout_hint"]["column"] = 99
        original["legacy_review"]["checked"] = True
        self.assertEqual(adapted.legacy_record, before)
        restored = reconstruct_legacy_document(adapted)
        restored["content"].clear()
        self.assertEqual(adapted.legacy_record, before)

    def test_conversion_is_deterministic(self):
        original = source_lesson()
        first = adapt_legacy_lesson(original).model_dump(mode="json")
        second = adapt_legacy_lesson(original).model_dump(mode="json")
        self.assertEqual(first, second)

    def test_nested_metadata_stays_aligned_with_content_order(self):
        adapted = adapt_legacy_lesson(source_lesson())
        nested = adapted.legacy_metadata["content_unmapped_fields"]
        self.assertEqual(len(nested), len(adapted.contract["content_blocks"]))
        self.assertEqual(nested[0]["layout_hint"], {"column": 1})
        self.assertEqual(nested[0]["source_page"], 17)
        self.assertEqual(nested[1]["source_page"], 18)

    def test_metadata_collision_preserves_original_and_generated_values(self):
        original = source_lesson()
        original["content_unmapped_fields"] = {"owner": "legacy", "items": [None, "kept"]}
        original["__adapter_generated_content_unmapped_fields_1__"] = {"sentinel": 1}
        original["__adapter_generated_content_unmapped_fields_2__"] = {"sentinel": 2}
        before = copy.deepcopy(original)

        adapted = adapt_legacy_lesson(original)
        metadata = adapted.legacy_metadata
        self.assertEqual(metadata["content_unmapped_fields"], original["content_unmapped_fields"])
        self.assertEqual(metadata["__adapter_generated_content_unmapped_fields_1__"], {"sentinel": 1})
        self.assertEqual(metadata["__adapter_generated_content_unmapped_fields_2__"], {"sentinel": 2})
        generated = metadata["__adapter_generated_content_unmapped_fields_3__"]
        self.assertEqual(len(generated), len(adapted.contract["content_blocks"]))
        self.assertEqual(generated[0]["layout_hint"], {"column": 1})
        self.assertEqual(generated[1]["source_page"], 18)
        self.assertEqual(original, before)
        self.assertEqual(reconstruct_legacy_document(adapted), before)

        serialized = adapted.model_dump(mode="json")
        self.assertEqual(reconstruct_legacy_document(serialized), before)
        self.assertEqual(adapt_legacy_lesson(original).model_dump(mode="json"), serialized)

    def test_noncollision_keeps_legacy_nested_metadata_key_unchanged(self):
        adapted = adapt_legacy_lesson(source_lesson())
        self.assertIn("content_unmapped_fields", adapted.legacy_metadata)
        self.assertEqual(adapted.legacy_metadata["content_unmapped_fields"][0]["layout_hint"], {"column": 1})
        self.assertFalse(any(key.startswith("__adapter_generated_") for key in adapted.legacy_metadata))

    def test_empty_missing_and_null_legacy_values_keep_existing_reconstruction(self):
        cases = [
            {"id": "l", "textbook_id": "b", "section_id": "s", "title": "L"},
            {"id": "l", "textbook_id": "b", "section_id": "s", "title": "L", "content": []},
            {"id": "l", "textbook_id": "b", "section_id": "s", "title": "L",
             "content": [], "content_unmapped_fields": None, "notes": []},
        ]
        for original in cases:
            with self.subTest(original=original):
                adapted = adapt_legacy_lesson(original)
                self.assertEqual(reconstruct_legacy_document(adapted), original)
                self.assertEqual(reconstruct_legacy_document(adapted.model_dump(mode="json")), original)

    def test_invalid_required_fields_ranges_provenance_and_json_values_fail(self):
        with self.assertRaises(ValueError):
            adapt_legacy_textbook({"id": "  ", "title": "T"})
        with self.assertRaises(ValueError):
            adapt_legacy_section({"id": "s", "textbook_id": "b", "order": -1, "title": "S"})
        with self.assertRaises(ValueError):
            adapt_legacy_lesson({
                "id": "l", "textbook_id": "b", "section_id": "s", "title": "L",
                "page_start": 8, "page_end": 7,
            })
        with self.assertRaises(ValueError):
            adapt_legacy_lesson({
                "id": "l", "textbook_id": "b", "section_id": "s", "title": "L",
                "content": [{"type": "explanation", "text": "x", "provenance": "GUESSED"}],
            })
        with self.assertRaises(ValueError):
            adapt_legacy_structured_content({"type": "task", "text": "x", "page_start": 0})
        with self.assertRaises(ValidationError):
            AdaptedLegacyRecord(
                entity_type="textbook", contract_type="SourceDocument", contract={},
                legacy_record={"id": "x", "not_json": object()},
            )


if __name__ == "__main__":
    unittest.main()
