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
        for index in range(page_count):
            page_number = index + 1
            page = document[index]
            page_warnings: list[dict[str, Any]] = []
            suspicious_span_counts: dict[str, int] = {}
            spans: list[dict[str, Any]] = []
            image_resources: list[dict[str, Any]] = []
            image_placements: list[dict[str, Any]] = []

            try:
                page_rect = page.rect
                width = _finite_number(page_rect.width)
                height = _finite_number(page_rect.height)
                if width is None or height is None or width <= 0 or height <= 0:
                    page_warnings.append({"code": "invalid_page_dimensions", "message": "Page dimensions are unavailable or invalid."})

                text_dict = page.get_text("dict", sort=False)
                span_order = 0
                for block_index, block in enumerate(text_dict.get("blocks", [])):
                    for line_index, line in enumerate(block.get("lines", [])):
                        for span_index, span in enumerate(line.get("spans", [])):
                            raw_text = span.get("text", "")
                            if not isinstance(raw_text, str):
                                raw_text = str(raw_text)
                            span_order += 1
                            box = _bbox(span.get("bbox"))
                            if box is None:
                                page_warnings.append({"code": "invalid_span_bbox", "message": f"Text span {span_order} has missing, non-finite, or degenerate geometry."})
                            font_size = _finite_number(span.get("size"))
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
                            })
                            if _suspicious_unicode(raw_text):
                                if "SourceSans" in str(span.get("font", "")):
                                    warning_code = "suspicious_source_font_text"
                                else:
                                    warning_code = "suspicious_text_encoding"
                                suspicious_span_counts[warning_code] = suspicious_span_counts.get(warning_code, 0) + 1

                # get_images reports page resources; get_image_info reports actual
                # raster placements. These are intentionally separate records.
                for resource_index, image in enumerate(page.get_images(full=True), start=1):
                    xref = int(image[0]) if image and image[0] is not None else 0
                    image_resources.append({
                        "id": f"sha256:{fingerprint}:p{page_number}:image-resource{resource_index}",
                        "pdf_page_number": page_number,
                        "resource_index": resource_index,
                        "xref": xref,
                        "width": int(image[2]) if len(image) > 2 else None,
                        "height": int(image[3]) if len(image) > 3 else None,
                        "bits_per_component": int(image[4]) if len(image) > 4 else None,
                        "colorspace": str(image[5]) if len(image) > 5 else None,
                        "soft_mask_xref": int(image[1]) if len(image) > 1 else None,
                    })
                for placement_index, info in enumerate(page.get_image_info(xrefs=True), start=1):
                    box = _bbox(info.get("bbox"))
                    if box is None:
                        page_warnings.append({"code": "invalid_image_bbox", "message": f"Raster placement {placement_index} has missing, non-finite, or degenerate geometry."})
                    xref_value = info.get("xref")
                    xref = int(xref_value) if xref_value is not None else 0
                    image_placements.append({
                        "id": f"sha256:{fingerprint}:p{page_number}:image-placement{placement_index}",
                        "pdf_page_number": page_number,
                        "placement_index": placement_index,
                        "xref": xref,
                        "bbox_pdf_points": box,
                        "width": int(info["width"]) if info.get("width") is not None else None,
                        "height": int(info["height"]) if info.get("height") is not None else None,
                        "x_resolution": int(info["xres"]) if info.get("xres") is not None else None,
                        "y_resolution": int(info["yres"]) if info.get("yres") is not None else None,
                        "colorspace_components": int(info["colorspace"]) if info.get("colorspace") is not None else None,
                        "bits_per_component": int(info["bpc"]) if info.get("bpc") is not None else None,
                    })
                for warning_code, span_count in suspicious_span_counts.items():
                    if warning_code == "suspicious_source_font_text":
                        message = "SourceSans text contains control or private-use characters; raw PyMuPDF text is retained without correction."
                    else:
                        message = "Text contains control or private-use characters; raw PyMuPDF text is retained without correction."
                    page_warnings.append({"code": warning_code, "message": message, "affected_span_count": span_count})
                if not any(span["raw_text"] for span in spans):
                    page_warnings.append({"code": "empty_extracted_text", "message": "No non-empty text spans were returned for this page; image-only, vector, blank, or non-text content is possible."})
            except Exception:
                page_warnings.append({"code": "page_extraction_error", "message": "Page extraction failed; available partial observations are retained."})

            if page_warnings:
                warnings.extend({"pdf_page_number": page_number, **warning} for warning in page_warnings)
            rect = page.rect
            page_width = _finite_number(rect.width)
            page_height = _finite_number(rect.height)
            pages.append({
                "id": f"sha256:{fingerprint}:p{page_number}",
                "pdf_page_number": page_number,
                "printed_page_number": None,
                "dimensions": {"width": page_width, "height": page_height, "unit": "pdf_points"},
                "coordinate_system": {"origin": "top_left", "unit": "pdf_points", "bbox_order": "x0,y0,x1,y1"},
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
            "limitations": list(_LIMITATIONS),
            "warnings": warnings,
            "pages": pages,
        }
    finally:
        document.close()
