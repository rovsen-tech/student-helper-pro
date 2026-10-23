"""Offline, read-only extraction of observable PDF text and image metadata.

The public entry point is :func:`extract_pdf`. It returns JSON-compatible data
and never infers textbook structure, printed page numbers, or corrected text.
"""
from __future__ import annotations

import hashlib
import math
import unicodedata
from pathlib import Path
from typing import Any

import pymupdf


EXTRACTOR_VERSION = "1.0.0"
SCHEMA_VERSION = "m2a.pdf-source-extraction.v1"
_LIMITATIONS = [
    "Text order and span boundaries follow PyMuPDF's extraction output and can vary across library versions.",
    "No OCR, semantic interpretation, printed-page inference, or text correction is performed.",
    "Image records describe PDF image resources and raster placements; vector drawings and text-based figures are not captured as images.",
]


class PDFExtractionError(Exception):
    """Base class for fatal document-level extraction errors."""


class InvalidPDFError(PDFExtractionError):
    """The supplied file could not be opened as a PDF."""


class PasswordProtectedPDFError(PDFExtractionError):
    """The PDF requires a password; this extractor does not accept passwords."""


class EmptyPDFError(PDFExtractionError):
    """The PDF contains no pages."""


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _finite_number(value: Any) -> float | None:
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None


def _bbox(rect: Any) -> list[float] | None:
    """Return a finite, non-degenerate [x0,y0,x1,y1] rectangle, if available."""
    try:
        coords = [_finite_number(v) for v in rect]
    except (TypeError, ValueError):
        return None
    if len(coords) != 4 or any(v is None for v in coords):
        return None
    x0, y0, x1, y1 = coords
    if x1 <= x0 or y1 <= y0:
        return None
    return [x0, y0, x1, y1]


def _suspicious_unicode(text: str) -> bool:
    """Detect clear extraction artifacts without attempting to repair text."""
    return any(
        (unicodedata.category(char) in {"Cc", "Cs", "Co"} and not char.isspace())
        for char in text
    )


def _span_id(fingerprint: str, page_number: int, order: int) -> str:
    return f"sha256:{fingerprint}:p{page_number}:span{order}"


def _aggregate_status(statuses: list[str]) -> str:
    if statuses and all(status == "failed" for status in statuses):
        return "failed"
    if statuses and all(status == "complete" for status in statuses):
        return "complete"
    return "partial"


def _optional_int(value: Any) -> int | None:
    try:
        return int(value) if value is not None else None
    except (TypeError, ValueError, OverflowError):
        return None


def extract_pdf(pdf_path: str | Path) -> dict[str, Any]:
    """Extract deterministic, JSON-serializable observations from a local PDF.

    Args:
        pdf_path: Path to a readable local PDF file. The path is not included in
            output. Passwords are not supported.

    Returns:
        A mapping with source-byte SHA-256, page count, library/schema versions,
        document warnings, and 1-based page records containing spans, image
        resources, and raster placements. Span ``raw_text`` is exactly what
        PyMuPDF returned. Coordinates are finite PDF points in PyMuPDF page
        space, with origin at the top-left; rectangles use [x0,y0,x1,y1].

    Raises:
        FileNotFoundError: The local file does not exist.
        InvalidPDFError: The file is unreadable or is not a valid PDF.
        PasswordProtectedPDFError: The PDF requires a password.
        EmptyPDFError: The PDF has zero pages.
    """
    path = Path(pdf_path)
    try:
        fingerprint = _sha256_file(path)
    except FileNotFoundError:
        raise
    except OSError as exc:
        raise InvalidPDFError("Unable to read the supplied PDF file") from exc
    try:
        document = pymupdf.open(str(path))
    except (pymupdf.FileDataError, RuntimeError, ValueError) as exc:
        raise InvalidPDFError("Unable to open the supplied file as a PDF") from exc

    try:
        if document.needs_pass:
            raise PasswordProtectedPDFError("Password-protected PDFs are not supported")
        page_count = len(document)
        if page_count == 0:
            raise EmptyPDFError("PDF contains no pages")

        warnings: list[dict[str, Any]] = []
        pages: list[dict[str, Any]] = []
        text_statuses: list[str] = []
        image_statuses: list[str] = []
        metadata_statuses: list[str] = []
        for index in range(page_count):
            page_number = index + 1
            page_warnings: list[dict[str, Any]] = []
            try:
                page = document[index]
            except (pymupdf.FileDataError, RuntimeError, ValueError):
                page_warnings.append({"code": "page_access_error", "message": "PyMuPDF could not access this page."})
                text_statuses.append("failed")
                image_statuses.append("failed")
                metadata_statuses.append("failed")
                warnings.extend({"pdf_page_number": page_number, **warning} for warning in page_warnings)
                pages.append({
                    "id": f"sha256:{fingerprint}:p{page_number}",
                    "pdf_page_number": page_number,
                    "printed_page_number": None,
                    "dimensions": {"width": None, "height": None, "unit": "pdf_points"},
                    "coordinate_system": {"origin": "top_left", "unit": "pdf_points", "bbox_order": "x0,y0,x1,y1"},
                    "extraction_status": {"text": "failed", "images": "failed", "image_resources": "failed", "image_placements": "failed", "page_metadata": "failed"},
                    "text_elements": [], "image_resources": [], "image_placements": [], "warnings": page_warnings,
                })
                continue
            page_width: float | None = None
            page_height: float | None = None
            metadata_status = "complete"
            try:
                page_rect = page.rect
                page_width = _finite_number(page_rect.width)
                page_height = _finite_number(page_rect.height)
            except (pymupdf.FileDataError, RuntimeError, ValueError):
                metadata_status = "failed"
                page_warnings.append({"code": "page_dimensions_error", "message": "Page dimensions could not be read."})
            if metadata_status == "complete" and (
                page_width is None or page_height is None or page_width <= 0 or page_height <= 0
            ):
                metadata_status = "partial"
                page_warnings.append({"code": "invalid_page_dimensions", "message": "Page dimensions are unavailable or invalid."})

            text_status = "complete"
            try:
                text_dict = page.get_text("dict", sort=False)
            except (pymupdf.FileDataError, RuntimeError, ValueError):
                text_dict = None
                text_status = "failed"
                page_warnings.append({"code": "text_extraction_error", "message": "PyMuPDF could not extract page text."})
            if text_status != "failed" and not isinstance(text_dict, dict):
                text_status = "failed"
                page_warnings.append({"code": "invalid_text_result", "message": "PyMuPDF returned an unsupported page-text result."})

            suspicious_span_counts: dict[str, int] = {}
            spans: list[dict[str, Any]] = []
            image_resources: list[dict[str, Any]] = []
            image_placements: list[dict[str, Any]] = []
            if text_status != "failed":
                span_order = 0
                text_blocks = text_dict.get("blocks", [])
                if not isinstance(text_blocks, list):
                    text_blocks = []
                    text_status = "partial"
                    page_warnings.append({"code": "invalid_text_blocks", "message": "PyMuPDF returned an unsupported block list."})
                for block_index, block in enumerate(text_blocks):
                    if not isinstance(block, dict):
                        text_status = "partial"
                        page_warnings.append({"code": "invalid_text_block", "message": f"Text block {block_index} has an unsupported record shape."})
                        continue
                    lines = block.get("lines", [])
                    if not isinstance(lines, list):
                        text_status = "partial"
                        page_warnings.append({"code": "invalid_text_lines", "message": f"Text block {block_index} has an unsupported line list."})
                        continue
                    for line_index, line in enumerate(lines):
                        if not isinstance(line, dict):
                            text_status = "partial"
                            page_warnings.append({"code": "invalid_text_line", "message": f"Text line {line_index} has an unsupported record shape."})
                            continue
                        line_spans = line.get("spans", [])
                        if not isinstance(line_spans, list):
                            text_status = "partial"
                            page_warnings.append({"code": "invalid_text_spans", "message": f"Text line {line_index} has an unsupported span list."})
                            continue
                        for span_index, span in enumerate(line_spans):
                            if not isinstance(span, dict):
                                text_status = "partial"
                                page_warnings.append({"code": "invalid_text_span", "message": f"Text span {span_index} has an unsupported record shape."})
                                continue
                            raw_text = span.get("text", "")
                            if not isinstance(raw_text, str):
                                raw_text = str(raw_text)
                            span_order += 1
                            box = _bbox(span.get("bbox"))
                            span_warnings: list[dict[str, str]] = []
                            if box is None:
                                warning = {"code": "invalid_span_bbox"}
                                span_warnings.append(warning)
                                page_warnings.append({**warning, "message": f"Text span {span_order} has missing, non-finite, or degenerate geometry."})
                                text_status = "partial"
                            font_size = _finite_number(span.get("size"))
                            if font_size is None:
                                warning = {"code": "invalid_span_font_size"}
                                span_warnings.append(warning)
                                page_warnings.append({**warning, "message": f"Text span {span_order} has missing or invalid font-size metadata."})
                                text_status = "partial"
                            spans.append({
                                "id": _span_id(fingerprint, page_number, span_order),
                                "pdf_page_number": page_number,
                                "order": span_order,
                                "block_index": block_index,
                                "line_index": line_index,
                                "span_index": span_index,
                                "raw_text": raw_text,
                                "font": span.get("font"),
                                "font_size": font_size,
                                "bbox_pdf_points": box,
                                "warnings": span_warnings,
                            })
                            if _suspicious_unicode(raw_text):
                                if "SourceSans" in str(span.get("font", "")):
                                    warning_code = "suspicious_source_font_text"
                                else:
                                    warning_code = "suspicious_text_encoding"
                                spans[-1]["warnings"].append({"code": warning_code})
                                suspicious_span_counts[warning_code] = suspicious_span_counts.get(warning_code, 0) + 1
                for warning_code, span_count in suspicious_span_counts.items():
                    text_status = "partial"
                    if warning_code == "suspicious_source_font_text":
                        message = "SourceSans text contains control or private-use characters; raw PyMuPDF text is retained without correction."
                    else:
                        message = "Text contains control or private-use characters; raw PyMuPDF text is retained without correction."
                    page_warnings.append({"code": warning_code, "message": message, "affected_span_count": span_count})
                if text_status != "failed" and not any(span["raw_text"] for span in spans):
                    page_warnings.append({"code": "empty_extracted_text", "message": "No non-empty text spans were returned for this page; image-only, vector, blank, or non-text content is possible."})

            resource_status = "complete"
            try:
                resource_entries = page.get_images(full=True)
            except (pymupdf.FileDataError, RuntimeError, ValueError):
                resource_entries = []
                resource_status = "failed"
                page_warnings.append({"code": "image_resource_extraction_error", "message": "PyMuPDF could not enumerate page image resources."})
            if not isinstance(resource_entries, (tuple, list)):
                resource_entries = []
                resource_status = "failed"
                page_warnings.append({"code": "invalid_image_resource_result", "message": "PyMuPDF returned an unsupported image-resource result."})
            for resource_index, image in enumerate(resource_entries, start=1):
                if not isinstance(image, (tuple, list)):
                    resource_status = "partial"
                    page_warnings.append({"code": "invalid_image_resource", "message": f"Image resource {resource_index} has an unsupported record shape."})
                    continue
                xref = _optional_int(image[0]) if len(image) > 0 else None
                width = _optional_int(image[2]) if len(image) > 2 else None
                height = _optional_int(image[3]) if len(image) > 3 else None
                bpc = _optional_int(image[4]) if len(image) > 4 else None
                soft_mask = _optional_int(image[1]) if len(image) > 1 else None
                if xref is None or width is None or height is None:
                    resource_status = "partial"
                    page_warnings.append({"code": "incomplete_image_resource", "message": f"Image resource {resource_index} has missing or invalid metadata."})
                image_resources.append({
                    "id": f"sha256:{fingerprint}:p{page_number}:image-resource{resource_index}",
                    "pdf_page_number": page_number,
                    "resource_index": resource_index,
                    "xref": xref if xref is not None else 0,
                    "width": width,
                    "height": height,
                    "bits_per_component": bpc,
                    "colorspace": str(image[5]) if len(image) > 5 else None,
                    "soft_mask_xref": soft_mask,
                })

            placement_status = "complete"
            try:
                placement_entries = page.get_image_info(xrefs=True)
            except (pymupdf.FileDataError, RuntimeError, ValueError):
                placement_entries = []
                placement_status = "failed"
                page_warnings.append({"code": "image_placement_extraction_error", "message": "PyMuPDF could not enumerate raster image placements."})
            if not isinstance(placement_entries, (tuple, list)):
                placement_entries = []
                placement_status = "failed"
                page_warnings.append({"code": "invalid_image_placement_result", "message": "PyMuPDF returned an unsupported image-placement result."})
            for placement_index, info in enumerate(placement_entries, start=1):
                if not isinstance(info, dict):
                    placement_status = "partial"
                    page_warnings.append({"code": "invalid_image_placement", "message": f"Raster placement {placement_index} has an unsupported record shape."})
                    continue
                box = _bbox(info.get("bbox"))
                xref = _optional_int(info.get("xref"))
                width = _optional_int(info.get("width"))
                height = _optional_int(info.get("height"))
                xres = _optional_int(info.get("xres"))
                yres = _optional_int(info.get("yres"))
                colorspace = _optional_int(info.get("colorspace"))
                bpc = _optional_int(info.get("bpc"))
                if box is None:
                    placement_status = "partial"
                    page_warnings.append({"code": "invalid_image_bbox", "message": f"Raster placement {placement_index} has missing, non-finite, or degenerate geometry."})
                if width is None or height is None:
                    placement_status = "partial"
                    page_warnings.append({"code": "incomplete_image_placement", "message": f"Raster placement {placement_index} has missing or invalid metadata."})
                image_placements.append({
                    "id": f"sha256:{fingerprint}:p{page_number}:image-placement{placement_index}",
                    "pdf_page_number": page_number,
                    "placement_index": placement_index,
                    "xref": xref if xref is not None else 0,
                    "bbox_pdf_points": box,
                    "width": width,
                    "height": height,
                    "x_resolution": xres,
                    "y_resolution": yres,
                    "colorspace_components": colorspace,
                    "bits_per_component": bpc,
                })

            image_status = _aggregate_status([resource_status, placement_status])
            text_statuses.append(text_status)
            image_statuses.append(image_status)
            metadata_statuses.append(metadata_status)
            if page_warnings:
                warnings.extend({"pdf_page_number": page_number, **warning} for warning in page_warnings)
            pages.append({
                "id": f"sha256:{fingerprint}:p{page_number}",
                "pdf_page_number": page_number,
                "printed_page_number": None,
                "dimensions": {"width": page_width, "height": page_height, "unit": "pdf_points"},
                "coordinate_system": {"origin": "top_left", "unit": "pdf_points", "bbox_order": "x0,y0,x1,y1"},
                "extraction_status": {
                    "text": text_status,
                    "images": image_status,
                    "image_resources": resource_status,
                    "image_placements": placement_status,
                    "page_metadata": metadata_status,
                },
                "text_elements": spans,
                "image_resources": image_resources,
                "image_placements": image_placements,
                "warnings": page_warnings,
            })

        return {
            "schema_version": SCHEMA_VERSION,
            "extractor_version": EXTRACTOR_VERSION,
            "extraction_library": {"name": "PyMuPDF", "version": str(pymupdf.VersionBind)},
            "source_sha256": fingerprint,
            "pdf_page_count": page_count,
            "extraction_status": {
                "text": _aggregate_status(text_statuses),
                "images": _aggregate_status(image_statuses),
                "page_metadata": _aggregate_status(metadata_statuses),
            },
            "limitations": list(_LIMITATIONS),
            "warnings": warnings,
            "pages": pages,
        }
    finally:
        document.close()
