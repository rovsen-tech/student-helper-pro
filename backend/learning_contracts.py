"""Version 1, persistence-ready learning contracts.

These models describe data only. They do not perform I/O, execute board actions,
grade answers, infer source facts, or create identifiers.
"""
from __future__ import annotations

import math
import re
from datetime import date, datetime
from typing import Annotated, Any, Literal, Union

from pydantic import BaseModel, ConfigDict, Field, PositiveInt, field_validator, model_validator


Provenance = Literal["SOURCE", "DERIVED", "GENERATED"]
JsonValue = Any


def _check_id(value: str) -> str:
    if not value or not value.strip() or value != value.strip():
        raise ValueError("identifier must be nonempty and have no surrounding whitespace")
    return value


def _check_optional_id(value: str | None) -> str | None:
    return None if value is None else _check_id(value)


def _check_ids(values: list[str], *, unique: bool = False) -> list[str]:
    for value in values:
        _check_id(value)
    if unique and len(values) != len(set(values)):
        raise ValueError("identifier list must not contain duplicates")
    return values


def _check_json(value: Any, path: str = "value") -> Any:
    """Accept JSON values only; reject Python objects, non-string keys and NaN/Infinity."""
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ValueError(f"{path} must contain only finite numbers")
        return value
    if isinstance(value, list):
        for index, item in enumerate(value):
            _check_json(item, f"{path}[{index}]")
        return value
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ValueError(f"{path} object keys must be strings")
            _check_json(item, f"{path}.{key}")
        return value
    raise ValueError(f"{path} must contain JSON-compatible values")


class ContractModel(BaseModel):
    """Closed JSON object: unknown fields fail instead of becoming executable extensions."""

    model_config = ConfigDict(extra="forbid", validate_assignment=True, allow_inf_nan=False)


class VersionedModel(ContractModel):
    schema_version: Literal[1]


class BoundingBox(ContractModel):
    """A rectangle with an explicit coordinate system; never inferred from page numbers."""

    x: float = Field(ge=0)
    y: float = Field(ge=0)
    width: float = Field(gt=0)
    height: float = Field(gt=0)
    coordinate_space: Literal["normalized", "pdf_points"]

    @model_validator(mode="after")
    def normalized_bounds(self):
        if self.coordinate_space == "normalized" and (
            self.x + self.width > 1 or self.y + self.height > 1
        ):
            raise ValueError("normalized bounding box must fit within 0..1")
        return self


class PageReference(ContractModel):
    """Printed and PDF page numbers are independent, optional facts."""

    printed_page: PositiveInt | None = None
    pdf_page: PositiveInt | None = None
    bbox: BoundingBox | None = None

    @model_validator(mode="after")
    def bbox_needs_pdf_page(self):
        if self.bbox is not None and self.pdf_page is None:
            raise ValueError("a bounding box requires an explicitly supplied PDF page")
        return self


class SourceReference(ContractModel):
    source_document_id: str
    content_node_id: str | None = None
    page_refs: list[PageReference] = Field(default_factory=list)

    _ids = field_validator("source_document_id")(_check_id)
    _optional_ids = field_validator("content_node_id")(_check_optional_id)


class MasteryCriteria(ContractModel):
    minimum_accuracy: float | None = Field(default=None, ge=0, le=1)
    minimum_evidence_count: PositiveInt | None = None
    rubric_id: str | None = None

    _rubric_id = field_validator("rubric_id")(_check_optional_id)


class ContentBlock(ContractModel):
    content_type: str
    provenance: Provenance
    text: str
    normalized_text: str | None = None
    original_text: str | None = None
    source_refs: list[SourceReference] = Field(default_factory=list)

    @field_validator("content_type")
    @classmethod
    def nonempty_type(cls, value: str) -> str:
        return _check_id(value)


class LearningProgram(VersionedModel):
    id: str
    program_type: Literal["school", "cefr", "ielts", "exam", "university", "law", "professional"]
    title: str | None = None
    jurisdiction: str | None = None
    framework_version: str | None = None
    locale: str | None = None
    level_scheme: str | None = None

    _ids = field_validator("id")(_check_id)


class SourceDocument(VersionedModel):
    id: str
    title: str
    document_type: str
    program_id: str | None = None
    edition: str | None = None
    effective_from: date | None = None
    revision: str | None = None
    file_hash: str | None = None
    source_uri: str | None = None
    original_asset: str | None = None
    ingestion_status: Literal["unknown", "pending", "ingested", "review_required", "approved", "rejected"] = "unknown"

    _ids = field_validator("id")(_check_id)
    _optional_ids = field_validator("program_id")(_check_optional_id)
    _title = field_validator("title", "document_type")(_check_id)

    @field_validator("file_hash")
    @classmethod
    def sha256_if_present(cls, value: str | None) -> str | None:
        if value is not None and not re.fullmatch(r"[0-9a-fA-F]{64}", value):
            raise ValueError("file_hash must be a 64-character SHA-256 hex digest")
        return value


class ContentNode(VersionedModel):
    id: str
    source_document_id: str
    parent_id: str | None = None
    node_type: str
    title: str | None = None
    order: int | None = Field(default=None, ge=0)
    page_refs: list[PageReference] = Field(default_factory=list)
    content_blocks: list[ContentBlock] = Field(default_factory=list)
    extraction_confidence: float | None = Field(default=None, ge=0, le=1)
    review_status: Literal["unknown", "pending", "approved", "rejected"] = "unknown"

    _ids = field_validator("id", "source_document_id")(_check_id)
    _optional_ids = field_validator("parent_id")(_check_optional_id)
    _node_type = field_validator("node_type")(_check_id)


class LearningObjective(VersionedModel):
    id: str
    program_id: str
    competency_id: str | None = None
    title: str | None = None
    prerequisites: list[str] = Field(default_factory=list)
    mastery_criteria: MasteryCriteria | None = None

    _ids = field_validator("id", "program_id")(_check_id)
    _optional_ids = field_validator("competency_id")(_check_optional_id)

    @field_validator("prerequisites")
    @classmethod
    def valid_unique_prerequisites(cls, values: list[str]) -> list[str]:
        for value in values:
            _check_id(value)
        if len(values) != len(set(values)):
            raise ValueError("prerequisites must be unique")
        return values


class LessonStep(ContractModel):
    id: str
    objective_ids: list[str] = Field(default_factory=list)
    source_node_ids: list[str] = Field(default_factory=list)
    explanation: str | None = None
    example: str | None = None

    _ids = field_validator("id")(_check_id)

    @field_validator("objective_ids", "source_node_ids")
    @classmethod
    def valid_reference_ids(cls, values: list[str]) -> list[str]:
        return _check_ids(values)


class PracticeBlueprint(ContractModel):
    objective_ids: list[str] = Field(default_factory=list)
    item_type: Literal["multiple_choice", "short_answer", "essay", "oral", "performance"]
    item_count: PositiveInt
    difficulty: float | None = Field(default=None, ge=0, le=1)

    @field_validator("objective_ids")
    @classmethod
    def valid_objective_ids(cls, values: list[str]) -> list[str]:
        return _check_ids(values)


class LessonPlan(VersionedModel):
    id: str
    program_id: str | None = None
    objective_ids: list[str] = Field(default_factory=list)
    ordered_source_node_ids: list[str] = Field(default_factory=list)
    explanation_steps: list[LessonStep] = Field(default_factory=list)
    practice_blueprint: list[PracticeBlueprint] = Field(default_factory=list)
    citations: list[SourceReference] = Field(default_factory=list)

    _ids = field_validator("id")(_check_id)
    _optional_ids = field_validator("program_id")(_check_optional_id)

    @field_validator("objective_ids", "ordered_source_node_ids")
    @classmethod
    def valid_reference_ids(cls, values: list[str]) -> list[str]:
        return _check_ids(values)


class BoardPoint(ContractModel):
    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)


class WriteTextPayload(ContractModel):
    kind: Literal["write_text"]
    text: str
    position: BoardPoint | None = None


class WriteMathPayload(ContractModel):
    kind: Literal["write_math"]
    expression: str
    position: BoardPoint | None = None


class DrawShapePayload(ContractModel):
    kind: Literal["draw_shape"]
    shape: Literal["line", "circle", "rectangle", "triangle"]
    points: list[BoardPoint] = Field(min_length=2, max_length=3)

    @model_validator(mode="after")
    def valid_point_count(self):
        expected = {"line": (2, 2), "circle": (2, 2), "rectangle": (2, 2), "triangle": (3, 3)}
        low, high = expected[self.shape]
        if not low <= len(self.points) <= high:
            raise ValueError(f"{self.shape} requires {low} point(s)")
        return self


class HighlightPayload(ContractModel):
    kind: Literal["highlight"]
    target_id: str

    _ids = field_validator("target_id")(_check_id)


class ClearPayload(ContractModel):
    kind: Literal["clear"]


BoardPayload = Annotated[
    Union[WriteTextPayload, WriteMathPayload, DrawShapePayload, HighlightPayload, ClearPayload],
    Field(discriminator="kind"),
]
BoardActionType = Literal["write_text", "write_math", "draw_shape", "highlight", "clear"]


class BoardAction(VersionedModel):
    id: str
    action_type: BoardActionType
    payload: BoardPayload
    lesson_step_id: str | None = None
    source_node_id: str | None = None
    timing_ms: int | None = Field(default=None, ge=0)

    _ids = field_validator("id")(_check_id)
    _optional_ids = field_validator("lesson_step_id", "source_node_id")(_check_optional_id)

    @model_validator(mode="after")
    def action_matches_payload(self):
        if self.action_type != self.payload.kind:
            raise ValueError("action_type must match payload kind")
        return self


class AssessmentPrivate(ContractModel):
    """Private evaluator fields; never returned by the student-facing projection."""

    answer_key: JsonValue = None
    distractor_rationale: list[str] = Field(default_factory=list)
    rubric: JsonValue = None
    evaluator_metadata: dict[str, JsonValue] = Field(default_factory=dict)
    private_metadata: dict[str, JsonValue] = Field(default_factory=dict)

    @field_validator("answer_key", "rubric", "evaluator_metadata", "private_metadata")
    @classmethod
    def only_json_data(cls, value: Any) -> Any:
        return _check_json(value)


class AssessmentItem(VersionedModel):
    id: str
    objective_ids: list[str] = Field(default_factory=list)
    difficulty: float | None = Field(default=None, ge=0, le=1)
    prompt: str | None = None
    response_type: Literal["multiple_choice", "short_answer", "essay", "oral", "performance"] = "short_answer"
    options: list[str] = Field(default_factory=list)
    validation_status: Literal["unknown", "pending", "validated", "rejected"] = "unknown"
    source_refs: list[SourceReference] = Field(default_factory=list)
    private: AssessmentPrivate = Field(default_factory=AssessmentPrivate)

    _ids = field_validator("id")(_check_id)

    @field_validator("objective_ids")
    @classmethod
    def valid_objective_ids(cls, values: list[str]) -> list[str]:
        return _check_ids(values)

    def student_facing_projection(self) -> dict[str, Any]:
        """Build an allowlisted public object without serializing private model fields."""
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "objective_ids": list(self.objective_ids),
            "difficulty": self.difficulty,
            "prompt": self.prompt,
            "response_type": self.response_type,
            "options": list(self.options),
            "source_refs": [reference.model_dump(mode="json") for reference in self.source_refs],
        }


class StudentEvidence(VersionedModel):
    id: str
    student_id: str
    objective_id: str
    item_id: str
    response: JsonValue = None
    rubric: JsonValue = None
    outcome: Literal["unknown", "unscored", "incorrect", "partial", "correct"] = "unknown"
    misconception_tags: list[str] = Field(default_factory=list)
    timestamp: datetime | None = None

    _ids = field_validator("id", "student_id", "objective_id", "item_id")(_check_id)
    _json = field_validator("response", "rubric")(_check_json)


class StudentMastery(VersionedModel):
    student_id: str
    objective_id: str
    estimate: float | None = Field(default=None, ge=0, le=1)
    confidence: float | None = Field(default=None, ge=0, le=1)
    last_practiced: datetime | None = None
    next_review_at: datetime | None = None
    algorithm_version: str | None = None

    _ids = field_validator("student_id", "objective_id")(_check_id)
    _optional_ids = field_validator("algorithm_version")(_check_optional_id)


class ExamBlueprint(VersionedModel):
    id: str
    program_id: str
    objective_weights: dict[str, float] = Field(default_factory=dict)
    difficulty_mix: dict[str, float] = Field(default_factory=dict)
    item_count: PositiveInt | None = None
    duration_seconds: PositiveInt | None = None
    access_policy: str | None = None

    _ids = field_validator("id", "program_id")(_check_id)

    @field_validator("objective_weights", "difficulty_mix")
    @classmethod
    def bounded_weights(cls, values: dict[str, float]) -> dict[str, float]:
        for key, value in values.items():
            _check_id(key)
            if not math.isfinite(value) or not 0 <= value <= 1:
                raise ValueError("weights must be finite values between 0 and 1")
        if values and not math.isclose(sum(values.values()), 1.0, abs_tol=1e-6):
            raise ValueError("a supplied weight distribution must sum to 1")
        return values
