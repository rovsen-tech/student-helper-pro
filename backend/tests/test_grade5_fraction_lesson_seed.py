"""Contract and arithmetic checks for the visually verified lesson excerpt."""
import json
from fractions import Fraction
from pathlib import Path
import unittest

from learning_contracts import ContentNode, SourceDocument


SEED_PATH = Path(__file__).parents[1] / "data" / "grade5_fraction_division_seed.json"
PDF_SHA256 = "ccd7a084ff36b50ccdc5a35f955df7e451fa28ff4dda346468924d5f0bc30d30"


class Grade5FractionLessonSeedTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.seed = json.loads(SEED_PATH.read_text(encoding="utf-8"))
        cls.source = SourceDocument.model_validate(cls.seed["source_document"])
        cls.node = ContentNode.model_validate(cls.seed["content_node"])
        cls.blocks = {block.content_type: block for block in cls.node.content_blocks}

    def test_seed_validates_and_source_references_match(self):
        self.assertEqual(self.source.file_hash, PDF_SHA256)
        self.assertEqual(self.source.ingestion_status, "review_required")
        self.assertEqual(self.node.review_status, "pending")
        self.assertEqual(self.node.page_refs[0].pdf_page, 73)
        self.assertEqual(self.node.page_refs[0].printed_page, 71)
        for block in self.node.content_blocks:
            self.assertTrue(block.source_refs)
            self.assertEqual(block.source_refs[0].source_document_id, self.source.id)
            self.assertEqual(block.source_refs[0].page_refs[0].pdf_page, 73)

    def test_source_and_derived_content_are_separate(self):
        for block_type in ("rule", "worked_example", "exercise"):
            self.assertEqual(self.blocks[block_type].provenance, "SOURCE")
        answers = self.blocks["calculated_answers"]
        self.assertEqual(answers.provenance, "DERIVED")
        self.assertNotIn("original_text", answers.model_fields_set)

    def test_worked_example_and_exercise_answers_are_arithmetically_correct(self):
        self.assertEqual(Fraction(1, 3) / 2, Fraction(1, 6))
        computed = [Fraction(1, 2) / 3, Fraction(2, 3) / 5, Fraction(4, 5) / 8]
        self.assertEqual(computed, [Fraction(1, 6), Fraction(2, 15), Fraction(1, 10)])
        self.assertEqual(self.blocks["calculated_answers"].text, "a) 1/6; b) 2/15; c) 1/10")


if __name__ == "__main__":
    unittest.main()
