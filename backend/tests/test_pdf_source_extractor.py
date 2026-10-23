import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pymupdf

import pdf_source_extractor as extractor


def _save_pdf(path, page_specs):
    document = pymupdf.open()
    for text in page_specs:
        page = document.new_page(width=300, height=400)
        if text:
            page.insert_text((30, 40), text, fontname="helv", fontsize=12)
    document.save(path)
    document.close()


class PDFSourceExtractorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def _extract_text(self, text="Traceable source text"):
        path = self.root / "fixture.pdf"
        _save_pdf(path, [text])
        return extractor.extract_pdf(path)

    def test_single_page_spans_font_geometry_and_json_serialization(self):
        result = self._extract_text()
        page = result["pages"][0]
        self.assertEqual(result["pdf_page_count"], 1)
        self.assertEqual(page["pdf_page_number"], 1)
        self.assertIsNone(page["printed_page_number"])
        self.assertEqual(page["dimensions"]["unit"], "pdf_points")
        span = page["text_elements"][0]
        self.assertEqual(span["raw_text"], "Traceable source text")
        self.assertEqual(span["font"], "Helvetica")
        self.assertGreater(span["font_size"], 0)
        self.assertEqual(len(span["bbox_pdf_points"]), 4)
        self.assertEqual(json.loads(json.dumps(result)), result)

    def test_multiple_pages_have_explicit_one_based_numbers_and_unique_ids(self):
        path = self.root / "multi.pdf"
        _save_pdf(path, ["first", "second", "third"])
        pages = extractor.extract_pdf(path)["pages"]
        self.assertEqual([p["pdf_page_number"] for p in pages], [1, 2, 3])
        ids = [p["id"] for p in pages]
        ids.extend(s["id"] for p in pages for s in p["text_elements"])
        self.assertEqual(len(ids), len(set(ids)))

    def test_unicode_azerbaijani_is_preserved_when_supported_by_builtin_font(self):
        source = "\u00f6l\u00e7\u00fc"
        path = self.root / "unicode.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        page.insert_text((30, 50), source, fontname="helv", fontsize=12)
        doc.save(path)
        doc.close()
        text = "".join(s["raw_text"] for s in extractor.extract_pdf(path)["pages"][0]["text_elements"])
        # These Latin-1 characters are representable by PyMuPDF's built-in Helvetica fixture.
        self.assertEqual(text, source)

    def test_empty_and_image_only_pages_are_reported_without_fabricated_text(self):
        path = self.root / "empty_image.pdf"
        doc = pymupdf.open()
        doc.new_page()
        image_page = doc.new_page()
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 2, 2), 0)
        pixmap.clear_with(220)
        image_page.insert_image(pymupdf.Rect(20, 20, 80, 80), pixmap=pixmap)
        doc.save(path)
        doc.close()
        pages = extractor.extract_pdf(path)["pages"]
        self.assertEqual(pages[0]["text_elements"], [])
        self.assertTrue(any(w["code"] == "empty_extracted_text" for w in pages[0]["warnings"]))
        self.assertEqual(pages[1]["text_elements"], [])
        self.assertEqual(len(pages[1]["image_resources"]), 1)
        self.assertEqual(len(pages[1]["image_placements"]), 1)
        self.assertEqual(pages[1]["image_placements"][0]["bbox_pdf_points"], [20.0, 20.0, 80.0, 80.0])

    def test_image_resources_and_actual_placements_are_distinct(self):
        path = self.root / "images.pdf"
        doc = pymupdf.open()
        page = doc.new_page()
        pixmap = pymupdf.Pixmap(pymupdf.csRGB, pymupdf.IRect(0, 0, 3, 4), 0)
        pixmap.clear_with(127)
        page.insert_image(pymupdf.Rect(10, 10, 40, 50), pixmap=pixmap)
        page.insert_image(pymupdf.Rect(60, 60, 120, 140), pixmap=pixmap)
        doc.save(path)
        doc.close()
        page_data = extractor.extract_pdf(path)["pages"][0]
        self.assertGreaterEqual(len(page_data["image_resources"]), 1)
        self.assertEqual(len(page_data["image_placements"]), 2)
        self.assertEqual(len({p["id"] for p in page_data["image_placements"]}), 2)
        self.assertEqual([p["bbox_pdf_points"] for p in page_data["image_placements"]], [[10.0, 10.0, 40.0, 50.0], [60.0, 60.0, 120.0, 140.0]])

    def test_repeated_extraction_is_deterministic_and_ids_change_with_source_bytes(self):
        first = self.root / "first.pdf"
        second = self.root / "second.pdf"
        _save_pdf(first, ["same content"])
        _save_pdf(second, ["different content"])
        one = extractor.extract_pdf(first)
        self.assertEqual(one, extractor.extract_pdf(first))
        two = extractor.extract_pdf(second)
        self.assertNotEqual(one["source_sha256"], two["source_sha256"])
        self.assertNotEqual(one["pages"][0]["id"], two["pages"][0]["id"])

    def test_missing_and_invalid_files_raise_explicit_errors(self):
        with self.assertRaises(FileNotFoundError):
            extractor.extract_pdf(self.root / "missing.pdf")
        invalid = self.root / "invalid.pdf"
        invalid.write_bytes(b"not a PDF")
        with self.assertRaises(extractor.InvalidPDFError):
            extractor.extract_pdf(invalid)

    def test_password_protected_document_is_rejected_and_closed(self):
        path = self.root / "encrypted.pdf"
        doc = pymupdf.open()
        doc.new_page().insert_text((20, 20), "secret")
        doc.save(path, encryption=pymupdf.PDF_ENCRYPT_AES_256, owner_pw="owner", user_pw="user")
        doc.close()
        opened = []

        actual_open = pymupdf.open
        def recording_open(*args, **kwargs):
            document = actual_open(*args, **kwargs)
            opened.append(document)
            return document
        with patch.object(extractor.pymupdf, "open", side_effect=recording_open):
            with self.assertRaises(extractor.PasswordProtectedPDFError):
                extractor.extract_pdf(path)
        self.assertTrue(opened[0].is_closed)

    def test_zero_page_pdf_is_a_fatal_document_error(self):
        path = self.root / "zero.pdf"
        objects = [b"<< /Type /Catalog /Pages 2 0 R >>", b"<< /Type /Pages /Kids [] /Count 0 >>"]
        data = bytearray(b"%PDF-1.4\n")
        offsets = []
        for number, body in enumerate(objects, start=1):
            offsets.append(len(data))
            data.extend(f"{number} 0 obj\n".encode() + body + b"\nendobj\n")
        xref_offset = len(data)
        data.extend(b"xref\n0 3\n0000000000 65535 f \n")
        for offset in offsets:
            data.extend(f"{offset:010} 00000 n \n".encode())
        data.extend(f"trailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n{xref_offset}\n%%EOF\n".encode())
        path.write_bytes(data)
        with self.assertRaises(extractor.EmptyPDFError):
            extractor.extract_pdf(path)

    def test_long_span_content_is_not_truncated(self):
        text = "long-source-" * 1800
        path = self.root / "long.pdf"
        doc = pymupdf.open()
        page = doc.new_page(width=1000, height=5000)
        pieces = [text[index:index + 100] for index in range(0, len(text), 100)]
        for line, piece in enumerate(pieces):
            page.insert_text((10, 20 + line * 14), piece, fontname="helv", fontsize=8)
        doc.save(path)
        doc.close()
        result = extractor.extract_pdf(path)
        extracted = "".join(span["raw_text"] for span in result["pages"][0]["text_elements"])
        self.assertEqual(extracted, text)
        self.assertGreater(len(extracted), 8000)

    def test_invalid_or_degenerate_geometry_is_omitted_safely(self):
        self.assertIsNone(extractor._bbox((0, 0, 0, 5)))
        self.assertIsNone(extractor._bbox((0, 0, float("nan"), 5)))
        self.assertIsNone(extractor._bbox((0, 0, float("inf"), 5)))
        self.assertEqual(extractor._bbox((-1, 2, 3, 5)), [-1.0, 2.0, 3.0, 5.0])


if __name__ == "__main__":
    unittest.main()
