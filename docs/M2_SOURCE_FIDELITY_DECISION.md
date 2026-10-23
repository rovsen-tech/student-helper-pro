# M2: source fidelity decision and first verified lesson excerpt

**M2-B0 status at that audit:** NEEDS SOURCE VERIFICATION

**M2-B1 status:** Selected excerpt visually verified; educator review remains pending.

**Topic:** Grade 5, section 2.8, division of common fractions

**Inspected asset:** `backend/mathbook.pdf`

**SHA-256:** `ccd7a084ff36b50ccdc5a35f955df7e451fa28ff4dda346468924d5f0bc30d30`

## M2-B0 decision snapshot

At the time of the M2-B0 audit, do not build the first AI lesson from the current extracted text or from the local `curriculum.py` entry. The PDF page is visually legible, but important title/body fonts produce incorrect PyMuPDF text and fraction layout is not preserved semantically. No reliable general decoder was established. That audit could verify the section title only. The M2-B1 visual review below supersedes that evidence limit for the specific rule, worked example, and first exercise transcribed below; it does not validate the rest of the page or an entire lesson.

## M2-B0 evidence snapshot

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

## M2-B1: visual verification and minimal M1 sample

The PDF was rendered read-only with PyMuPDF to a temporary PNG and opened for direct visual inspection. The render was not saved in the repository. PDF page 73 shows printed page 71. The following visible text was transcribed directly from the page image and compared with the misencoded PyMuPDF text; it was not reconstructed from the damaged strings.

| Claim/content | PDF location | Provenance and check | Status |
|---|---|---|---|
| `Bölmə əməlini bölənin tərsi olan ədədə vurma ilə əvəz etmək olar.` | Page 73, text near `[56.7, 384.5, 411.7, 399.5]` PDF points; raw dict block 28, line 0, spans 0-1. | SOURCE; transcribed from rendered page and checked against the visible sentence. | verified |
| `1/3 : 2 = 1/3 · 1/2 = 1/6` | Page 73, formula near `[216.2, 570.1, 307.4, 593.9]` PDF points; raw dict block 34, text spans 0-12 include separate digits/operators. | SOURCE; visually transcribed. Separately calculated `Fraction(1, 3) / 2 = Fraction(1, 6)`. | verified |
| Exercise 1: `Təsvirlərə uyğun bölmə əməlini yazın və qisməti tapın.` Subparts: `a) 1/2 : 3`, `b) 2/3 : 5`, `c) 4/5 : 8`. | Page 73, instruction near `[62.3, 631.9, 376.1, 649.2]` PDF points; diagrams and labels around y=656-714. Numerator/denominator glyphs and division labels occur as separate spans; diagrams are visual. | SOURCE; full instruction and all three diagram expressions checked against the rendered page. | verified |
| Exercise results: `a) 1/6; b) 2/15; c) 1/10` | Derived only from the three verified expressions above; no textbook answer key is asserted. | DERIVED; independently calculated with exact rational arithmetic: `1/2 / 3`, `2/3 / 5`, `4/5 / 8`. | verified calculation; not a SOURCE answer |

The offline sample is [grade5_fraction_division_seed.json](../backend/data/grade5_fraction_division_seed.json). It validates as M1 `SourceDocument`, `ContentNode`, `ContentBlock`, and `PageReference` data. Every block points to the PDF document and page 73 / printed page 71. The source document remains `review_required` and the node remains `pending`; those statuses avoid implying educator approval. The three transcribed source blocks use `SOURCE`; the separately calculated results use `DERIVED` and have no `original_text`.

The excerpt is visually verified against this PDF, not independently reviewed by a math educator or publisher. Beyond these exact items, the surrounding explanation, any additional examples, the official answer key, and pedagogical correctness remain unverified. This seed is not a complete interactive lesson.

## Tests and scope

M2-B0 preflight was on branch `architecture/universal-learning-os` at expected HEAD `fd8ff166b4b339ee8a08f0adb3c0d7851119a6f`. M2-B1 preflight confirmed the same branch, HEAD `1e23d214a0def5d23cf6a0263d287111e77498bc`, clean worktree, and the PDF hash above. Runtime versions were Python 3.12.10, PyMuPDF 1.28.2, and Pydantic 2.13.4 (the requirements file pins Pydantic 2.13.5; no packages were installed).

Ran from `backend`: `python -m unittest tests.test_learning_contracts tests.test_learning_adapters tests.test_pdf_source_extractor tests.test_grade5_fraction_lesson_seed` - **37 tests passed** (34 existing M1/M2-A tests and 3 new seed/arithmetic tests). PDF inspection and extraction were read-only; the temporary rendered image was opened for visual inspection. No application/importer/server import, database access, PDF modification, dependency change, or existing-data mutation was performed.

## Next step

Have a math educator review the visually transcribed excerpt and independently check the derived exercise results. Then verify the remaining lesson content and any official answer key against an authoritative source before drafting the first interactive lesson. Keep the PDF raw extraction unchanged and retain this reviewed transcription as a separate source-grounded seed.
