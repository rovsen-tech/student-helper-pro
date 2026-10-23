# M2-A Offline PDF Source Extraction

## Scope and interface

`backend/pdf_source_extractor.py` is an isolated, read-only observer. It accepts a local PDF path and returns JSON-serializable Python data through `extract_pdf(path)`. It does not import or execute `ingest_textbook.py` or `server.py`, read environment secrets, call services, write output files, or persist records. This separation is necessary because the existing textbook importer initializes MongoDB and deletes/replaces curriculum records.

The extractor uses PyMuPDF 1.28.2 and Python standard-library facilities. Its output includes the SHA-256 of source PDF bytes, schema and extractor versions, runtime library version, 1-based PDF page numbers, page dimensions, spans, image observations, warnings, and extraction statuses. It does not infer printed page numbers, textbook metadata, learning structure, or corrected text. No machine-specific path is returned.

```python
from pdf_source_extractor import extract_pdf

result = extract_pdf("backend/mathbook.pdf")
```

Text span records retain the exact PyMuPDF `raw_text`, explicit page association, source order, font, size, and optional bounding box. IDs derive from file SHA-256, PDF page, and local element order. Repeating extraction with the same bytes and library version returns equivalent data. Element ordering can change across PyMuPDF versions.

Coordinates use PDF points in PyMuPDF page space, origin at the top-left, with boxes represented as `[x0, y0, x1, y1]`. Non-finite and degenerate boxes are set to `null` and warned about; no geometry is fabricated. M1 bounding boxes require a separate positive-width/height and non-negative-origin check.

## Extraction status and warnings

Both document and page records have `extraction_status`. The separate `text` and `images` fields use `complete`, `partial`, or `failed`. Page records also expose `image_resources`, `image_placements`, and `page_metadata` statuses. `complete` means the extraction calls and required metadata completed without detected errors; it is not a guarantee that source glyphs were encoded correctly. Suspicious text marks the text channel `partial`. Invalid image geometry marks its image channel `partial`. If a page operation fails, the remaining channel can still complete; if all pages fail for a channel, its document status is `failed`.

Every suspicious text span has its own `warnings` entry, while the page warning summarizes the affected span count. `suspicious_source_font_text` identifies suspect SourceSans spans; `suspicious_text_encoding` identifies suspicious spans from other fonts. In both cases, `raw_text` is unchanged. The extractor does not hide unexpected programming errors behind a broad catch. It catches known PyMuPDF/runtime failures around page dimensions and each text/image API call, records the relevant failure, and continues the other extraction channels. Malformed geometry and incomplete image metadata produce recoverable warnings and partial status.

Fatal document errors are explicit: missing paths raise `FileNotFoundError`; unreadable or invalid PDFs raise `InvalidPDFError`; encrypted PDFs raise `PasswordProtectedPDFError`; and zero-page PDFs raise `EmptyPDFError`. The PyMuPDF handle closes in a `finally` block.

## Textbook fidelity investigation

### Visual and extracted-text comparison

Representative pages were rendered in memory for visual comparison and inspected with raw PyMuPDF spans. No image, PDF, or extraction-result file was written.

- **PDF page 11** visibly shows the heading `1.1. Natural \u0259d\u0259dl\u0259r` and readable Azerbaijani body text. PyMuPDF returns SegoeUI spans such as `*\x81Q\u02ce\u00fbG...`, and some spans are only control characters. The visible footer is 9; that observation is not copied into `printed_page_number`.
- **PDF page 73** visibly shows `2.8. Adi k\u0259sl\u0259rin b\u00f6l\u00fcnm\u0259si`, explanatory prose, fraction diagrams, and exercise text. Poppins-Bold heading spans contain modifier/Greek-looking code points and controls instead of the visible Azerbaijani title. SegoeUI exercise prose is similarly encoded-looking. The rendered lower exercise includes fractions 1/2, 2/3, and 4/5; extraction exposes numerator and denominator spans separately, while bars and diagram layout do not become a reliable fraction relation. The visible footer is 71, whereas this is PDF page 73.
- **PDF page 123** also has readable rendered prose but SegoeUI raw spans with control characters and sequences such as `&\u02ceGY...`. It is another example of the failure outside SourceSans.
- **PDF page 143** contains readable Times New Roman Azerbaijani spans. A representative short sample, rendered via HTML entities to preserve Unicode in this file, is &#x00DC;mumi t&#x0259;hsil m&#x00FC;&#x0259;ssis&#x0259;l&#x0259;rinin 5-ci sinifl&#x0259;ri &#x00FC;&#x00E7;&#x00FC;n.

The visually correct mathematical diagrams and printed text do not establish that formulas, fraction bars, reading order, or their semantic relations were extracted correctly. Some digits/operators are separate spans or drawn elements.

### Font-map evidence and decoder review

The existing `ingest_textbook.py` was read as source only; it was not imported or executed. Its `_decode_span()` applies a `+0x1D` character shift and a small override table only to font names containing `SourceSans`.

Inspection of the actual PDF font dictionaries confirms missing Unicode mappings in several used embedded font resources:

- On PDF page 73, the Poppins-Bold Type0 resource uses `Identity-H` and has no `/ToUnicode` entry. The SegoeUI-Bold resource also has no `/ToUnicode` entry.
- The SegoeUI Type0 resource used on pages 11 and 73 uses `Identity-H` without `/ToUnicode`.
- The SourceSans Type1 resource has a custom encoding but no `/ToUnicode` entry.

The same page contains other font resources with ToUnicode maps, so this is not evidence that every font or span is defective. For the selected page-73 SourceSans span, raw text `\x04\x03\n\x03` becomes `! ' ` under a diagnostic reimplementation of the legacy shift/override rule; that does not match the visible badge `2.8.`. The Poppins and SegoeUI heading/body spans are not covered by the legacy rule at all. These observations support missing/incomplete source font-to-Unicode mapping as a major cause, but do not determine whether the PDF producer's maps, font subset encoding, or PyMuPDF's fallback handling is responsible for every affected span. The exact original glyph-to-Unicode map is not recoverable from the evidence inspected so far.

No correction is applied and no `derived_text` is emitted. A generic shift or guessed mapping would risk silently changing mathematical symbols, Azerbaijani letters, and exercise text.

## Images and M1 boundary

`image_resources` reports per-page entries from `Page.get_images(full=True)`; `image_placements` reports raster placements from `Page.get_image_info(xrefs=True)`. Both include available references, dimensions, and geometry without exporting image bytes. Counts are resource entries and placements, not unique image binaries and not a claim that every figure was captured. Vector drawings, text-based diagrams, mathematical meaning, LaTeX, question/answer relations, OCR, and lesson structure are out of scope.

The observed SHA-256 can later support `SourceDocument.file_hash`; PDF page number and valid point geometry can support M1 `PageReference` and `BoundingBox`; span IDs/positions can inform later source references. This phase does not create `ContentNode` records or make a persistence/API integration.

## Tests and smoke findings

Run from `backend/`:

```powershell
python -m unittest tests.test_pdf_source_extractor
python -m unittest tests.test_learning_contracts tests.test_learning_adapters
python -m unittest tests.test_smart_notes tests.test_speech_preparation tests.test_quiz_progress
```

The offline fixtures cover raw-span preservation and per-span warnings, page and channel statuses after failures, dimensions errors, deterministic IDs/results, Unicode fixture text, image resource/placement distinctions, empty pages, invalid/password-protected PDFs, cleanup, long text, JSON serialization, and invalid geometry. They need no network, OCR, MongoDB, API keys, or external services.

Latest run: 16 extractor tests passed; 18 M1 tests passed; the selected related backend regression suites ran 71 tests, with 69 passed and 2 skipped. The skips were endpoint/model test setup requiring `motor` and `mongomock_motor`. Both new Python files compiled. The full backend suite was not run.

Read-only smoke test on `backend/mathbook.pdf` with PyMuPDF 1.28.2:

- SHA-256: `ccd7a084ff36b50ccdc5a35f955df7e451fa28ff4dda346468924d5f0bc30d30`.
- 144 PDF pages, 23,573 text spans, 1,475 image-resource entries, and 1,552 raster placements.
- Pages 2 and 4 returned no non-empty text spans.
- 33 SourceSans spans across 33 pages and 8,919 other-font spans across 139 pages contained control/private-use characters. Three placements had invalid boxes. No page extraction API failed in this smoke run.
- Document status: text `partial`, images `partial`, page metadata `complete`. The text status reflects the observed encoding concerns; image status reflects the invalid placements.

### Not yet verified

The correct Unicode text for all affected spans, complete figure/layout fidelity, mathematical formula reconstruction, printed-page mappings throughout the book, extraction consistency across library versions, and any M1 persistence mapping remain unverified. No source text was corrected or treated as authoritative.

## Next steps and non-goals

For reliable text, obtain the original editable source or authoritative per-font ToUnicode/CID-to-glyph mappings from the PDF producer. Build a reviewed corpus that pairs glyph codes with rendered evidence across Azerbaijani letters, headings, fractions, operators, and exercises. Validate any proposed mapping against unseen pages and visual samples before exposing separate derived text. If authoritative mappings cannot be obtained, assess OCR as a separately scoped future option with human review; do not overwrite raw spans.

M2-A does not run the importer, persist records, infer curriculum, perform OCR/LLM processing, generate explanations or answers, alter APIs, or deploy. M2-B requires independent review of this schema and a separately approved text-fidelity plan. This code is a review candidate, not a production-readiness claim.
