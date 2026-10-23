# M2-B0: source fidelity decision for the first math lesson

**Status: NEEDS SOURCE VERIFICATION**

**Topic:** Grade 5, section 2.8, division of common fractions

**Inspected asset:** `backend/mathbook.pdf`

**SHA-256:** `ccd7a084ff36b50ccdc5a35f955df7e451fa28ff4dda346468924d5f0bc30d30`

## Decision

Do not build the first AI lesson from the current extracted text or from the local `curriculum.py` entry. The PDF page is visually legible, but important title/body fonts produce incorrect PyMuPDF text and fraction layout is not preserved semantically. No reliable general decoder was established. The most efficient safe route is to obtain a small, human-verified lesson excerpt with explicit source references, then encode only that reviewed excerpt. This is not enough evidence to author a lesson now: the example below verifies the section title only.

## Evidence sample

| Content | Source location | Provenance | Check | Status |
|---|---|---|---|---|
| `2.8. Adi k&#x0259;sl&#x0259;rin b&#x00F6;l&#x00FC;nm&#x0259;si` (section title as visibly printed) | PDF page 73; printed footer 71. Rendered title near `[114.5, 57.8, 386.5, 88.6]` PDF points. PyMuPDF source spans `sha256:ccd7a084ff36b50ccdc5a35f955df7e451fa28ff4dda346468924d5f0bc30d30:p73:span2`, `span4`, `span6` have null normalized boxes and corrupted raw text. | SOURCE | Rendered page compared directly with raw text spans; title is readable in the page image and does not match extracted characters. | verified (visual title only) |
| Diagram labels visibly include `1/2`, `2/3`, and `4/5` | PDF page 73; lower diagram, approximately y=656-714 PDF points. Numerator and denominator are separate PyMuPDF spans; bars/placement are not represented as fraction relationships. | SOURCE | Rendered page compared with page text/layout; the fractions are visual observations, not reconstructed from extraction. | needs_review (not a machine-ready expression) |
| Exercise prose and its mathematical instructions | PDF page 73; raw PyMuPDF text dictionary block 5, line 0, span 0 at `[87.2, 631.9, 376.1, 647.8]` PDF points. | SOURCE | Rendered page visibly contains an exercise, but the full exact wording, symbols, and relation to the nearby diagram have not been transcribed and checked. | unusable for lesson ingestion |

`verified` above applies only to the visible title string. No exercise wording, rule, worked solution, answer, or lesson plan is certified by this sample. In particular, a page render can verify visible marks but does not by itself prove pedagogical correctness or recover unambiguous math structure.

## PDF comparison and likely failure cause

PDF page 73 renders a readable Azerbaijani title, explanatory text, diagrams, and exercise. PyMuPDF's Poppins-Bold heading span is instead a sequence of modifier/Greek-looking code points and a control character; the SourceSans badge span is `\\x04\\x03\\n\\x03`; SegoeUI exercise/body spans also contain control and shifted-looking characters. Some numeric glyphs are returned as separate spans. Fractions appear as separate numerator and denominator text plus visual bars/layout, so extraction does not provide a dependable fraction object. PyMuPDF reports the page text channel as `partial`; image extraction is `complete` and metadata is `complete`. Those statuses describe extraction calls and detected anomalies, not the truth of the textbook text.

The inspected page's embedded font dictionaries confirm missing `/ToUnicode` entries for Poppins-Bold (Type0, Identity-H), SegoeUI-Bold (Type0, Identity-H), SegoeUI Type0 (Identity-H), and SourceSans Type1 (custom encoding). Other font resources on that page do have `/ToUnicode`; therefore the issue is not universal. This is strong evidence that incomplete/missing font-to-Unicode mappings contribute to the wrong extracted characters. It does not prove that this is the sole cause for every span or distinguish the PDF producer's font subset/encoding from reader fallback behavior.

The old `_decode_span()` in `backend/ingest_textbook.py` was inspected as source only. It applies a `+0x1D` shift and a small override table only to SourceSans names; it does not cover the Poppins or SegoeUI spans. Applied diagnostically to the SourceSans sample, it yields punctuation that does not match the visible `2.8.` badge. No decoder was imported or run, and no guessed correction or derived text was created. The original glyph-to-Unicode mapping is not established by this audit.

## Local alternatives and M1 fit

- `backend/curriculum.py` has a broad `Adi k&#x0259;sl&#x0259;r` topic with generic outcomes/problems, not a section for division of common fractions. Its Azerbaijani strings are visibly mojibake in the source file; its provenance and alignment to this textbook page are not established. It is not a safe substitute.
- `backend/ingest_textbook.py` is the apparent source of legacy textbook lesson records: its configuration names section 2.8 at printed page 73, then it slices and labels extracted PDF text as `SOURCE`. The importer has no evidence in its code that those slices were visually verified. It was not imported or executed, and no MongoDB records were queried; live lesson-record provenance therefore remains unverified.
- Local tests contain hand-authored contract/adaptor fixtures, not authoritative curriculum content. Existing AI test notes and architecture/audit documents are not primary textbook sources.
- M1 can represent a source document with the PDF hash, a page reference with `pdf_page=73` and independently known `printed_page=71`, and source blocks. Its current `ContentNode`/`ContentBlock` contract does not encode this evidence table's per-claim verification status or span-level review state. Do not promote the needs-review fraction/task observations to an approved lesson node. Keep this evidence record separate until the content and review status have an agreed representation.

No independent local source was found that verifies the teaching explanation, examples, task wording, or answers for this exact lesson. No external source was searched.

## Tests and scope

Preflight confirmed branch `architecture/universal-learning-os`, expected HEAD `fd8ff166b4b339ee8a08f0adb3c0d7851119a6f`, clean worktree, and the PDF hash above. Runtime versions were Python 3.12.10, PyMuPDF 1.28.2, and Pydantic 2.13.4 (the requirements file pins Pydantic 2.13.5; no packages were installed).

Ran from `backend`: `python -m unittest tests.test_learning_contracts tests.test_learning_adapters tests.test_pdf_source_extractor` - **34 tests passed**. PDF inspection and extraction were in-memory/read-only. No application/importer/server import, database access, PDF write, dependency change, or existing-data mutation was performed.

## Next step

Ask a math educator or authorized textbook owner to verify a minimal excerpt for this exact lesson against the original page, including the rule, one worked example, and one exercise with all fraction bars/operators and any answer key checked independently. Record each item with PDF page, bounding box or span evidence, reviewer, verification method, and review status. If the printed PDF is ambiguous, request the publisher/source document with usable text mappings or an editable master. Only then map approved items into M1 source blocks and draft the first lesson; keep extracted raw text unchanged and preserve any reviewed transcription separately as derived text.
