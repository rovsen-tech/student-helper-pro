# M2-A Offline PDF Source Extraction

## Scope and isolation

`backend/pdf_source_extractor.py` is a standalone, offline observation layer. It accepts a local PDF path and returns a Python mapping; it does not import or call `ingest_textbook.py` or `server.py`, read environment variables, contact services, persist output, or change textbook records. This isolation matters because the existing importer creates a MongoDB client and deletes/replaces curriculum records as part of ingestion.

The extractor uses the repository-pinned PyMuPDF 1.28.2 API and Python standard-library hashing, path, Unicode-category and JSON-compatible types. It does not export image bytes, run OCR or an LLM, or infer learning structure.

## Interface and output

```python
from pdf_source_extractor import extract_pdf

observations = extract_pdf("backend/mathbook.pdf")
```

`extract_pdf(path)` returns a deterministic JSON-serializable mapping for a fixed PDF byte sequence, extractor version and PyMuPDF version. The top-level fields are:

- `schema_version`: `m2a.pdf-source-extraction.v1`.
- `extractor_version`: `1.0.0`.
- `extraction_library`: actual PyMuPDF name and runtime version.
- `source_sha256`: SHA-256 of the source PDF bytes, read in binary chunks.
- `pdf_page_count`, `pages`, and document-level `warnings`.
- `limitations`: known limitations of the extraction method.

No absolute or machine-specific path is returned. Each page has a stable identifier, explicit 1-based `pdf_page_number`, `printed_page_number: null`, dimensions, coordinate declaration, `text_elements`, `image_resources`, `image_placements`, and page warnings. Each text element includes its explicit page number, page-local 1-based order, stable identifier, block/line/span indices, exact PyMuPDF `raw_text`, font name, font size and an optional bounding box. No text is truncated or replaced with a normalized string.

Page dimensions and coordinates use PDF points in PyMuPDF page space: origin at the top-left, positive x rightward and positive y downward. Bounding boxes use `[x0, y0, x1, y1]`. Finite, non-degenerate rectangles are retained as observed, including negative origins if the source geometry has them. Invalid or degenerate rectangles become `null` and produce a structured warning; no replacement geometry is fabricated. Conversion to M1 `BoundingBox` must separately verify non-negative origin and positive dimensions before computing width and height.

## IDs and determinism

Document identity is the source-byte SHA-256. Page, text-span, image-resource and image-placement IDs combine that fingerprint with the explicit PDF page and the element's extraction order. They contain no random UUID, timestamp or path. Identical bytes under the same extractor/library version produce equivalent output in the focused test. Element order follows PyMuPDF's page, block, line, span and image-info ordering; this is not promised stable across library versions, which are reported in the result.

## Text fidelity and Azerbaijani fonts

`raw_text` is PyMuPDF's text returned for each span, including unusual Unicode/control characters. The extractor does not apply the old importer's `_decode_span()` rewrite and does not publish a guessed corrected value as authoritative. Clear control, surrogate or private-use characters add aggregated page warnings (`affected_span_count`): `suspicious_source_font_text` for SourceSans and `suspicious_text_encoding` for other fonts. Raw values are preserved. This is a signal for review, not a complete text-quality classifier.

The textbook smoke test found normal Azerbaijani text in Times New Roman spans on PDF page 143. For example, a short raw sample is “Ümumi təhsil müəssisələrinin 5-ci sinifləri üçün”. It also found 33 SourceSans spans with control characters. On PDF page 73, one raw SourceSans span was `\x04\x03\n\x03`; applying the legacy shift/override algorithm diagnostically to that selected span yielded `! ' `, which is not credible source text. The issue is broader than SourceSans: raw spans from SegoeUI and Poppins on page 73 also contain control characters and shifted-looking strings. This confirms that a blanket correction is unsafe. Raw text is preserved, and affected spans remain unverified. The fixture test checks Azerbaijani Latin characters supported by the built-in Helvetica encoding; it does not validate the textbook's broken font mappings.

## Images, figures and mathematics

`image_resources` reports each page resource entry returned by `Page.get_images(full=True)`, including available xref, dimensions, bit depth, colorspace and soft-mask references. `image_placements` reports actual raster placements returned by `Page.get_image_info(xrefs=True)`, including placement index, xref, geometry, pixel dimensions, resolution and available color metadata. They are separate because a resource and its page placements are different observations. No image binaries are exported.

These fields do not capture every visual figure. Vector drawings, mathematical diagrams, text-built figures, reading order, formula structure, mathematical meaning, question/answer relationships and lesson boundaries are not inferred. Retained span positions may support later layout work, but do not establish that a page's visual or mathematical content is correct.

## Errors and warnings

The extractor raises `FileNotFoundError` for a missing path, `InvalidPDFError` for an unreadable/non-PDF file, `PasswordProtectedPDFError` for a PDF requiring a password, and `EmptyPDFError` for a zero-page PDF. Passwords are intentionally not accepted. The PyMuPDF document is closed in a `finally` block, including fatal password and empty-document cases.

Recoverable page conditions are represented by structured warnings, including empty extracted text, invalid page/span/image geometry, suspicious SourceSans text and page extraction errors. Empty text does not establish that a page is blank; it may contain image, vector, outlined or otherwise non-extractable content. A page warning does not turn a fatal document failure into a successful result.

## M1 compatibility boundary

The output can support a later reviewed mapping to `SourceDocument.file_hash` (`source_sha256`), `PageReference.pdf_page` (`pdf_page_number`) and `BoundingBox` in `pdf_points` where its positive dimensions/origin satisfy M1 validation. Span IDs and positions can inform future content-node source references. This phase deliberately returns extraction observations rather than `ContentNode` records: title, edition, printed page, curriculum identity, hierarchy, provenance classification and educational meaning are not established by the observations. No M1 contract or adapter was changed, and this is not a migration or persistence integration.

## Tests and commands

Run from `backend/`:

```powershell
python -m unittest tests.test_pdf_source_extractor
python -m unittest tests.test_learning_contracts tests.test_learning_adapters
python -m unittest tests.test_smart_notes tests.test_speech_preparation tests.test_quiz_progress
```

The extractor tests generate PDFs locally in temporary directories with PyMuPDF. They cover page numbering, raw span fidelity, font/geometry metadata, Azerbaijani characters supported by the fixture font, empty/image-only pages, distinct image resources and placements, deterministic IDs, source-byte hashes, fatal file/password/empty-document errors, document cleanup, JSON serialization, long text and invalid geometry. They require no MongoDB, API keys, internet, OCR or service startup.

## Smoke-test findings

### Verified by tests

- PyMuPDF 1.28.2 opened generated single-page, multi-page, image-only, encrypted and long-text fixtures.
- The 11 extractor tests passed, including checks for raw text, explicit page numbering, JSON serialization, SHA-256 differences and cleanup after a password error.
- 18 M1 contract/adapter tests passed. The selected related backend regression suites ran 71 tests: 69 passed and 2 were skipped.
- The two new Python files compiled successfully.

### Observed in the actual textbook

- `backend/mathbook.pdf` SHA-256: `ccd7a084ff36b50ccdc5a35f955df7e451fa28ff4dda346468924d5f0bc30d30`.
- PyMuPDF 1.28.2 reported 144 pages and the extractor returned 23,573 text spans.
- The extractor returned 1,475 per-page image-resource entries and 1,552 raster placements. These are observations/entries, not counts of unique image binaries or a completeness claim.
- Pages 2 and 4 had no non-empty extracted text. The run flagged 33 SourceSans spans across 33 pages and 8,919 other-font spans across 139 pages for control/private-use characters. It also reported 3 invalid image-placement boxes and no page-extraction errors.
- Page 143 produced the Azerbaijani Times New Roman sample above. Page 73 contained a SourceSans span with control characters; the selected diagnostic application of the legacy decoder did not produce credible text.

### Not yet verified

- Correctness of SourceSans repair across the book, full visual/layout fidelity, vector-figure coverage, mathematical interpretation, printed-page mappings, reading order, and semantic textbook structure.
- Whether PyMuPDF ordering and extraction behavior are equivalent across versions or platforms.
- M1 persistence mapping, production use, performance limits for arbitrary large/untrusted PDFs, and any database or API integration.

The textbook smoke check only extracted metadata/text observations and summary counts. It did not render or dump the book, write extraction output, or access any database or network service.

## Non-goals and M2-B entry criteria

M2-A does not correct source text, infer printed pages, identify textbook metadata, build a curriculum tree, extract LaTeX, classify exercises, generate explanations/answers, perform OCR, create content nodes, update MongoDB, alter API behavior or approve an ingestion workflow.

Move to M2-B only after independent review accepts this extraction boundary and schema, a separately scoped plan defines source-font verification against representative visual pages, image/vector and math requirements are explicit, and any proposed M1 mapping or persistence work has its own compatibility, dry-run and rollback review. This implementation is a review candidate, not a production-readiness claim.
