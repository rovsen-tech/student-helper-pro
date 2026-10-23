"""Offline validation tests for the versioned, subject-neutral contract set."""
import json
import unittest

from pydantic import ValidationError

from learning_contracts import (
    AssessmentItem,
    BoardAction,
    ContentBlock,
    ContentNode,
    ExamBlueprint,
    LearningObjective,
    LearningProgram,
    LessonPlan,
    PageReference,
    SourceDocument,
    StudentEvidence,
    StudentMastery,
)


class ContractConstructionTests(unittest.TestCase):
    def test_all_ten_contracts_validate_and_json_serialize(self):
        program = LearningProgram(
            schema_version=1, id="az-grade-5", program_type="school",
            title="Mathematics", jurisdiction="AZ", locale="az-AZ", level_scheme="grade",
        )
        cefr = LearningProgram(
            schema_version=1, id="cefr-en", program_type="cefr", locale="en-GB", level_scheme="A1-C2",
        )
        law_program = LearningProgram(
            schema_version=1, id="law-az", program_type="law", jurisdiction="AZ",
            framework_version="2026-01", level_scheme="professional",
        )
        source = SourceDocument(
            schema_version=1, id="book-math-5", title="Mathematics", document_type="textbook",
            program_id=program.id, edition=None, ingestion_status="pending",
        )
        objective = LearningObjective(
            schema_version=1, id="obj-fractions", program_id=program.id,
            competency_id="fractions.compare", title="Compare fractions",
        )
        block = ContentBlock(
            content_type="explanation", provenance="SOURCE", text="Compare equal denominators.",
        )
        node = ContentNode(
            schema_version=1, id="lesson-1", source_document_id=source.id, node_type="lesson",
            title="Fractions", order=1,
            page_refs=[PageReference(printed_page=12, pdf_page=None)], content_blocks=[block],
        )
        plan = LessonPlan(
            schema_version=1, id="plan-1", program_id=program.id,
            objective_ids=[objective.id], ordered_source_node_ids=[node.id],
            explanation_steps=[{"id": "step-1", "objective_ids": [objective.id], "source_node_ids": [node.id]}],
            practice_blueprint=[{"objective_ids": [objective.id], "item_type": "short_answer", "item_count": 2}],
        )
        action = BoardAction(
            schema_version=1, id="action-1", action_type="write_math",
            payload={"kind": "write_math", "expression": "1/2 + 1/4"},
        )
        item = AssessmentItem(
            schema_version=1, id="item-1", objective_ids=[objective.id], prompt="Which is larger?",
            private={"answer_key": "1/2", "rubric": {"criteria": ["compare" ]}},
        )
        evidence = StudentEvidence(
            schema_version=1, id="evidence-1", student_id="student-1", objective_id=objective.id,
            item_id=item.id, response={"text": "1/2"}, outcome="unknown",
        )
        mastery = StudentMastery(
            schema_version=1, student_id="student-1", objective_id=objective.id,
            estimate=None, confidence=None,
        )
        exam = ExamBlueprint(
            schema_version=1, id="exam-1", program_id=law_program.id,
            objective_weights={"law.contracts": 0.7, "law.cases": 0.3},
            difficulty_mix={"introductory": 0.4, "advanced": 0.6}, item_count=20, duration_seconds=3600,
        )

        values = [program, cefr, law_program, source, node, objective, plan, action, item, evidence, mastery, exam]
        persisted_types = {
            LearningProgram, SourceDocument, ContentNode, LearningObjective, LessonPlan, BoardAction,
            AssessmentItem, StudentEvidence, StudentMastery, ExamBlueprint,
        }
        self.assertEqual({type(value) for value in values}, persisted_types)
        for value in values:
            with self.subTest(contract=type(value).__name__):
                encoded = json.dumps(value.model_dump(mode="json"), sort_keys=True)
                self.assertIsInstance(json.loads(encoded), dict)
                self.assertEqual(value.schema_version, 1)

    def test_page_reference_never_conflates_printed_and_pdf_pages(self):
        printed_only = PageReference(printed_page=17)
        pdf_only = PageReference(pdf_page=22)
        unknown = PageReference()
        self.assertIsNone(printed_only.pdf_page)
        self.assertIsNone(pdf_only.printed_page)
        self.assertIsNone(unknown.printed_page)
        self.assertIsNone(unknown.pdf_page)

    def test_ids_ranges_provenance_and_numeric_bounds_are_validated(self):
        with self.assertRaises(ValidationError):
            LearningProgram(schema_version=1, program_type="school")
        with self.assertRaises(ValidationError):
            LearningProgram(schema_version=1, id="  ", program_type="school")
        with self.assertRaises(ValidationError):
            PageReference(printed_page=0)
        with self.assertRaises(ValidationError):
            PageReference(pdf_page=2, bbox={"x": 0.8, "y": 0, "width": 0.4, "height": 0.2, "coordinate_space": "normalized"})
        with self.assertRaises(ValidationError):
            PageReference(bbox={"x": 0, "y": 0, "width": 1, "height": 1, "coordinate_space": "pdf_points"})
        with self.assertRaises(ValidationError):
            ContentBlock(content_type="text", provenance="UNVERIFIED", text="x")
        with self.assertRaises(ValidationError):
            ContentNode(schema_version=1, id="node", source_document_id="src", node_type="lesson", order=-1)
        with self.assertRaises(ValidationError):
            LessonPlan(schema_version=1, id="plan", objective_ids=[" "])
        with self.assertRaises(ValidationError):
            ContentNode(schema_version=1, id="node", source_document_id="src", node_type="lesson", extraction_confidence=1.1)
        with self.assertRaises(ValidationError):
            AssessmentItem(schema_version=1, id="item", difficulty=-0.1)
        with self.assertRaises(ValidationError):
            ExamBlueprint(schema_version=1, id="exam", program_id="law", item_count=0)
        with self.assertRaises(ValidationError):
            ExamBlueprint(schema_version=1, id="exam", program_id="law", objective_weights={"a": 0.7, "b": 0.7})
        with self.assertRaises(ValidationError):
            SourceDocument(schema_version=1, id="source", title="Book", document_type="textbook", file_hash="abc")

    def test_board_action_is_closed_and_payload_specific(self):
        valid = [
            ("write_text", {"kind": "write_text", "text": "Hello"}),
            ("write_math", {"kind": "write_math", "expression": "x + 1"}),
            ("draw_shape", {"kind": "draw_shape", "shape": "triangle", "points": [{"x": 0, "y": 0}, {"x": 1, "y": 0}, {"x": 0.5, "y": 1}]}),
            ("highlight", {"kind": "highlight", "target_id": "shape-1"}),
            ("clear", {"kind": "clear"}),
        ]
        for action_type, payload in valid:
            with self.subTest(action_type=action_type):
                action = BoardAction(schema_version=1, id=f"a-{action_type}", action_type=action_type, payload=payload)
                self.assertEqual(action.action_type, action.payload.kind)
        with self.assertRaises(ValidationError):
            BoardAction(schema_version=1, id="bad", action_type="run_script", payload={"kind": "clear"})
        with self.assertRaises(ValidationError):
            BoardAction(schema_version=1, id="bad", action_type="clear", payload={"kind": "write_text", "text": "x"})
        with self.assertRaises(ValidationError):
            BoardAction(schema_version=1, id="bad", action_type="write_text", payload={"kind": "write_text", "text": "x", "script": "alert(1)"})
        with self.assertRaises(ValidationError):
            BoardAction(schema_version=1, id="bad", action_type="draw_shape", payload={"kind": "draw_shape", "shape": "triangle", "points": [{"x": 0, "y": 0}]})

    def test_assessment_public_projection_excludes_nested_private_data(self):
        item = AssessmentItem(
            schema_version=1, id="q-1", objective_ids=["obj-1"], prompt="Choose.", options=["A", "B"],
            private={
                "answer_key": {"selected": "A", "secret": {"token": "private"}},
                "rubric": {"criteria": [{"score": 1, "answer_key": "hidden"}]},
                "evaluator_metadata": {"model": "private-evaluator"},
                "private_metadata": {"nested": {"rubric": "never public"}},
            },
        )
        public = item.student_facing_projection()
        encoded = json.dumps(public)
        for secret in ("answer_key", "private-evaluator", "never public", "private"):
            self.assertNotIn(secret, encoded)
        self.assertEqual(set(public), {
            "schema_version", "id", "objective_ids", "difficulty", "prompt",
            "response_type", "options", "source_refs",
        })


if __name__ == "__main__":
    unittest.main()
