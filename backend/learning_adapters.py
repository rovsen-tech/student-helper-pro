"""Pure adapters from the repository's legacy textbook dictionaries.

No server/importer imports, environment reads, persistence, ID generation or I/O.
"""
from __future__ import annotations

import copy
from collections.abc import Mapping
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from learning_contracts import (
    ContentBlock,
    ContentNode,
    LearningProgram,
    SourceDocument,
    _check_id,
    _check_json,
)


class AdaptedLegacyRecord(BaseModel):
    """A typed view plus isolated legacy metadata and an exact JSON source snapshot."""

    model_config = ConfigDict(extra="forbid")

    adapter_version: Literal[1] = 1
    entity_type: Literal["textbook", "section", "lesson", "structured_content"]
    contract_type: Literal["SourceDocument", "ContentNode", "ContentBlock"]
    contract: dict[str, Any]
    legacy_metadata: dict[str, Any] = Field(default_factory=dict)
    legacy_record: dict[str, Any]

    @field_validator("contract", "legacy_metadata", "legacy_record")
    @classmethod
    def json_compatible(cls, value: dict[str, Any]) -> dict[str, Any]:
        _check_json(value)
        return value

    @model_validator(mode="after")
    def entity_contract_agree(self):
        expected = {
            "textbook": "SourceDocument",
            "section": "ContentNode",
            "lesson": "ContentNode",
            "structured_content": "ContentBlock",
        }
        if self.contract_type != expected[self.entity_type]:
            raise ValueError("entity_type and contract_type do not match")
        return self


def _snapshot(document: Mapping[str, Any]) -> dict[str, Any]:
    if not isinstance(document, Mapping):
        raise TypeError("legacy document must be a mapping")
    result = dict(document)
    if any(not isinstance(key, str) for key in result):
        raise ValueError("legacy document keys must be strings")
    _check_json(result, "legacy document")
    return copy.deepcopy(result)


def _required_string(record: dict[str, Any], field: str) -> str:
    if field not in record or not isinstance(record[field], str):
        raise ValueError(f"legacy {field} is required and must be a string")
    return _check_id(record[field])


def _required_text(record: dict[str, Any], field: str) -> str:
    if field not in record or not isinstance(record[field], str):
        raise ValueError(f"legacy {field} is required and must be a string")
    return record[field]


def _optional_string(record: dict[str, Any], field: str, default: str | None = None) -> str | None:
    value = record[field] if field in record else default
    if value is not None and not isinstance(value, str):
        raise ValueError(f"legacy {field} must be a string or null")
    return value


def _order(record: dict[str, Any]) -> int:
    value = record.get("order", 0)
    if value is None:
        raise ValueError("legacy order cannot be null")
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError("legacy order must be a nonnegative integer or null")
    return value


def _page_fields(record: dict[str, Any]) -> None:
    for field in ("page_start", "page_end", "source_page"):
        value = record.get(field)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or value < 1):
            raise ValueError(f"legacy {field} must be a positive integer or null")
    start, end = record.get("page_start"), record.get("page_end")
    if start is not None and end is not None and start > end:
        raise ValueError("legacy page_start cannot be greater than page_end")


def _extra(record: dict[str, Any], mapped: set[str]) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in record.items() if key not in mapped}


def _adapted(
    *, entity_type: str, contract_type: str, contract: BaseModel,
    record: dict[str, Any], metadata: dict[str, Any],
) -> AdaptedLegacyRecord:
    return AdaptedLegacyRecord(
        entity_type=entity_type,
        contract_type=contract_type,
        contract=contract.model_dump(mode="json"),
        legacy_metadata=metadata,
        legacy_record=record,
    )


def _content_block(document: Mapping[str, Any]) -> tuple[ContentBlock, dict[str, Any], dict[str, Any]]:
    record = _snapshot(document)
    content_type = _required_string(record, "type")
    text = _required_text(record, "text")
    provenance = record.get("provenance", "SOURCE")
    if provenance not in ("SOURCE", "DERIVED", "GENERATED"):
        raise ValueError("legacy provenance must be SOURCE, DERIVED, or GENERATED")
    normalized = _optional_string(record, "normalized_text", "")
    original = _optional_string(record, "original_text", "")
    _page_fields(record)
    block = ContentBlock(
        content_type=content_type,
        provenance=provenance,
        text=text,
        normalized_text=normalized,
        original_text=original,
    )
    mapped = {"type", "provenance", "text", "normalized_text", "original_text"}
    return block, _extra(record, mapped), record


def adapt_legacy_textbook(document: Mapping[str, Any]) -> AdaptedLegacyRecord:
    """Map a legacy textbook to SourceDocument without asserting edition/page facts."""
    record = _snapshot(document)
    source = SourceDocument(
        schema_version=1,
        id=_required_string(record, "id"),
        title=_required_string(record, "title"),
        document_type="textbook",
        edition=_optional_string(record, "edition"),
    )
    return _adapted(
        entity_type="textbook",
        contract_type="SourceDocument",
        contract=source,
        record=record,
        metadata=_extra(record, {"id", "title", "edition"}),
    )


def adapt_legacy_section(document: Mapping[str, Any]) -> AdaptedLegacyRecord:
    """Map a legacy section to a ContentNode; original fields remain recoverable."""
    record = _snapshot(document)
    node = ContentNode(
        schema_version=1,
        id=_required_string(record, "id"),
        source_document_id=_required_string(record, "textbook_id"),
        node_type="section",
        title=_required_string(record, "title"),
        order=_order(record),
    )
    return _adapted(
        entity_type="section",
        contract_type="ContentNode",
        contract=node,
        record=record,
        metadata=_extra(record, {"id", "textbook_id", "title", "order"}),
    )


def adapt_legacy_lesson(document: Mapping[str, Any]) -> AdaptedLegacyRecord:
    """Map a legacy lesson and its blocks, retaining ambiguous page fields verbatim."""
    record = _snapshot(document)
    content = record.get("content", [])
    if not isinstance(content, list):
        raise ValueError("legacy lesson content must be a list")
    content_blocks: list[ContentBlock] = []
    nested_metadata: list[dict[str, Any]] = []
    for item in content:
        if not isinstance(item, Mapping):
            raise ValueError("each legacy lesson content item must be a mapping")
        block, metadata, _ = _content_block(item)
        content_blocks.append(block)
        nested_metadata.append(metadata)
    _page_fields(record)
    node = ContentNode(
        schema_version=1,
        id=_required_string(record, "id"),
        source_document_id=_required_string(record, "textbook_id"),
        parent_id=_required_string(record, "section_id"),
        node_type="lesson",
        title=_required_string(record, "title"),
        order=_order(record),
        content_blocks=content_blocks,
    )
    unmapped = _extra(record, {"id", "textbook_id", "section_id", "title", "order", "content"})
    if any(nested_metadata):
        unmapped["content_unmapped_fields"] = nested_metadata
    return _adapted(
        entity_type="lesson",
        contract_type="ContentNode",
        contract=node,
        record=record,
        metadata=unmapped,
    )


def adapt_legacy_structured_content(document: Mapping[str, Any]) -> AdaptedLegacyRecord:
    """Map a content block while keeping page_start/end/source_page as legacy-only facts."""
    block, metadata, record = _content_block(document)
    return _adapted(
        entity_type="structured_content",
        contract_type="ContentBlock",
        contract=block,
        record=record,
        metadata=metadata,
    )


def reconstruct_legacy_document(adapted: AdaptedLegacyRecord | Mapping[str, Any]) -> dict[str, Any]:
    """Return the exact supported JSON-compatible legacy shape captured by an adapter."""
    if isinstance(adapted, AdaptedLegacyRecord):
        record = adapted.legacy_record
    elif isinstance(adapted, Mapping):
        record = AdaptedLegacyRecord.model_validate(adapted).legacy_record
    else:
        raise TypeError("adapted must be an AdaptedLegacyRecord or its serialized mapping")
    _check_json(record, "legacy record")
    return copy.deepcopy(record)
