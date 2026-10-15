"""Reusable deterministic textbook ingestion pipeline.

PDF -> Textbook -> Section -> Lesson -> page-linked StructuredContent (provenance=SOURCE).

Reuse for a new book by passing a different CONFIG (metadata + structure).
Run once:  python ingest_textbook.py
Idempotent: stable ids + replace/upsert, so re-running does NOT duplicate.
"""
import os
import re
import sys
import asyncio
from pathlib import Path
from datetime import datetime, timezone

from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient
import pymupdf

ROOT = Path(__file__).parent
load_dotenv(ROOT / ".env")

client = AsyncIOMotorClient(os.environ["MONGO_URL"])
db = client[os.environ["DB_NAME"]]

# Pedagogical heading markers -> content_type (order independent; matched by appearance)
HEADINGS = [
    ("Araşdırma-müzakirə", "investigation"),
    ("Araşdırma - müzakirə", "investigation"),
    ("Öyrənmə", "explanation"),
    ("Yadda saxla", "rule"),
    ("Yaddaş saxla", "rule"),
    ("Diqqət", "note"),
    ("Fikirləş", "think"),
    ("Məsələ həlli", "worked_example"),
    ("Çalışma", "task"),
    ("Riyaziyyat tarixindən", "note"),
    ("XÜLASƏ", "summary"),
]

# ---- CONFIG: this edition is the SOURCE OF TRUTH ----
MATH_CONFIG = {
    "textbook_id": "tb-riyaziyyat-5-2024",
    "subject_id": "riyaziyyat",
    "title": "Riyaziyyat 5-ci sinif — Dərslik — 1-ci hissə",
    "grade": "5-ci sinif",
    "edition": "2024",
    "grif": "2024-019",
    "provenance": "SOURCE",
    "total_pages_hint": 144,
    "answers": {"printed_page": 142, "printed_end": 144},
    # unique titles used only to auto-detect printed->pdf page offset
    "offset_anchors": [
        ("Düzgün kəsrlər", 39),
        ("Faiz, adi kəsr", 123),
        ("Ədədin faizi", 127),
        ("Onluq kəsrlərin yuvarlaqlaşdırılması", 91),
    ],
    "sections": [
        {"id": "s1", "title": "Natural ədədlər və onlar üzərində əməllər", "lessons": [
            ("1.1", "İlkin yoxlama", 8),
            ("1.2", "Natural ədədlər", 9),
            ("1.3", "Müqayisə və sıralama", 13),
            ("1.4", "Natural ədədlərin toplanması və çıxılması", 18),
            ("1.5", "Natural ədədlərin vurulması və kubu", 23),
            ("1.6", "Natural ədədlərin bölməsi", 25),
            ("1.7", "Ədədi ifadələr", 27),
            ("1.8", "Ədədin bölünəni və bölənləri", 32),
            ("1.X", "Xülasə", 36),
            ("1.U", "Ümumiləşdirici tapşırıqlar", 37),
        ]},
        {"id": "s2", "title": "Adi kəsrlər", "lessons": [
            ("2.1", "Düzgün kəsrlər və düzgün olmayan kəsrlər", 39),
            ("2.2", "Müqayisə və sıralama", 43),
            ("2.3", "Məxrəcləri müxtəlif kəsrlərin toplanması və çıxılması", 47),
            ("2.4", "Qarışıq ədədlərin toplanması", 51),
            ("2.5", "Qarışıq ədədlərin çıxılması", 56),
            ("2.6", "Adi kəsrlərin vurulması", 64),
            ("2.7", "Qarışıq ədədlərin vurulması", 67),
            ("2.8", "Adi kəsrlərin bölünməsi", 73),
            ("2.9", "Qarışıq ədədlərin bölünməsi", 75),
            ("2.X", "Xülasə", 82),
            ("2.U", "Ümumiləşdirici tapşırıqlar", 83),
        ]},
        {"id": "s3", "title": "Onluq kəsrlər", "lessons": [
            ("3.1", "Onluq kəsrlər", 87),
            ("3.2", "Müqayisə və sıralama", 89),
            ("3.3", "Onluq kəsrlərin yuvarlaqlaşdırılması", 91),
            ("3.4", "Adi kəsrin onluq kəsrə çevrilməsi", 93),
            ("3.5", "Onluq kəsrlərin toplanması və çıxılması", 96),
            ("3.6", "Onluq kəsrlərin 10-un qüvvətlərinə vurulması və bölünməsi", 102),
            ("3.7", "Onluq kəsrlərin natural ədədə vurulması", 105),
            ("3.8", "Onluq kəsrlərin vurulması", 107),
            ("3.9", "Onluq kəsrin natural ədədə bölünməsi", 109),
            ("3.10", "Ədədin onluq kəsrə bölünməsi", 112),
            ("3.X", "Xülasə", 118),
            ("3.U", "Ümumiləşdirici tapşırıqlar", 119),
        ]},
        {"id": "s4", "title": "Faiz", "lessons": [
            ("4.1", "Faiz, adi kəsr, onluq kəsr", 123),
            ("4.2", "Ədədin faizi", 127),
            ("4.3", "Faizə görə ədədin tapılması", 130),
            ("4.4", "Kəmiyyətin qiymətinin müəyyən faiz artırılması və azaldılması", 132),
            ("4.X", "Xülasə", 135),
            ("4.U", "Ümumiləşdirici tapşırıqlar", 136),
        ]},
    ],
    # printed page after the last lesson content (boundary)
    "content_boundary_printed": 138,
}

SPECIAL_TYPE = {"X": "summary", "U": "task"}


def norm(txt):
    return re.sub(r"\s+", " ", (txt or "")).strip()


# This PDF embeds a subset font whose ToUnicode map is broken: glyph code + 0x1D = real char.
# Azerbaijani letters / punctuation sit at out-of-range codes -> explicit overrides.
_SHIFT = 0x1D
_OVERRIDES = {
    0x2ce: "ə", 0x2cd: "Ə", 0xd6: "ı", 0x81: "ü", 0x7c: "ö", 0xfb: "ş",
    0xf8: "ç", 0xf9: "ğ", 0x87: "—", 0xc3: "İ", 0x2dc: "", 0x2df: "",
    0x2e5: "", 0x2d4: "", 0x2e1: "", 0x2e6: "",
}


def _decode_span(text, font):
    # Correctly-encoded spans (non-subset fonts) are kept literal.
    if "SourceSans" not in (font or ""):
        return text
    out = []
    for ch in text:
        o = ord(ch)
        if o in _OVERRIDES:
            out.append(_OVERRIDES[o])
            continue
        d = o + _SHIFT
        out.append(chr(d) if 0x20 <= d <= 0x7E else " ")
    return "".join(out)


def extract_pages(pdf_path):
    doc = pymupdf.open(pdf_path)
    pages = []
    for pg in doc:
        d = pg.get_text("dict")
        buf = []
        for b in d.get("blocks", []):
            for ln in b.get("lines", []):
                for sp in ln.get("spans", []):
                    buf.append(_decode_span(sp.get("text", ""), sp.get("font", "")))
                buf.append(" ")
            buf.append("\n")
        pages.append("".join(buf))
    doc.close()
    return pages


def detect_offset(pages, anchors):
    """Find printed->pdf offset. pdf_index(0-based) = printed_page - 1 + offset."""
    found = []
    for title, printed in anchors:
        probe = norm(title).lower()[:18]
        for i, txt in enumerate(pages):
            if probe and probe in norm(txt).lower():
                found.append((i + 1) - printed)  # pdf_1based - printed
                break
    if not found:
        return 0
    found.sort()
    return found[len(found) // 2]  # median


def split_blocks(text):
    """Split a lesson body into provenance=SOURCE blocks by pedagogical headings."""
    marks = []
    for marker, ctype in HEADINGS:
        for m in re.finditer(re.escape(marker), text):
            marks.append((m.start(), ctype, marker))
    marks.sort()
    blocks = []
    intro = text[: marks[0][0]] if marks else text
    if norm(intro):
        blocks.append(("explanation", intro))
    for idx, (pos, ctype, _marker) in enumerate(marks):
        end = marks[idx + 1][0] if idx + 1 < len(marks) else len(text)
        chunk = text[pos:end]
        if norm(chunk):
            blocks.append((ctype, chunk))
    return blocks


async def ingest(pdf_path, cfg):
    pages = extract_pages(pdf_path)
    total = len(pages)
    offset = detect_offset(pages, cfg["offset_anchors"])
    print(f"PDF pages={total} detected_offset={offset}")

    def pdf_slice(printed_start, printed_end):
        a = max(0, printed_start - 1 + offset)
        b = min(total, printed_end - 1 + offset + 1)
        return "\n".join(pages[a:b]), (a + 1), min(total, b)

    tb_id = cfg["textbook_id"]
    # Clean old records for THIS textbook + any legacy placeholder for the subject
    await db.lessons.delete_many({"textbook_id": tb_id})
    await db.sections.delete_many({"textbook_id": tb_id})
    await db.answer_keys.delete_many({"textbook_id": tb_id})
    await db.textbooks.delete_many({"id": tb_id})
    await db.textbooks.delete_many({"id": "tb-riyaziyyat-5"})
    await db.sections.delete_many({"textbook_id": "tb-riyaziyyat-5"})
    await db.lessons.delete_many({"textbook_id": "tb-riyaziyyat-5"})

    now = datetime.now(timezone.utc).isoformat()
    await db.textbooks.replace_one({"id": tb_id}, {
        "id": tb_id, "subject_id": cfg["subject_id"], "title": cfg["title"],
        "grade": cfg["grade"], "edition": cfg["edition"], "grif": cfg["grif"],
        "provenance": cfg["provenance"], "created_at": now,
    }, upsert=True)

    # Flatten all lesson anchors to compute page_end = next anchor printed - 1
    flat = []
    for s_order, sec in enumerate(cfg["sections"], start=1):
        for num, title, printed in sec["lessons"]:
            flat.append({"section": sec, "s_order": s_order, "num": num, "title": title, "printed": printed})
    boundary = cfg["content_boundary_printed"]

    n_sections = 0
    n_lessons = 0
    n_blocks = 0
    pages_covered = set()

    for s_order, sec in enumerate(cfg["sections"], start=1):
        sec_id = f"{tb_id}-{sec['id']}"
        await db.sections.replace_one({"id": sec_id}, {
            "id": sec_id, "textbook_id": tb_id, "order": s_order, "title": sec["title"],
        }, upsert=True)
        n_sections += 1

        for l_order, (num, title, printed) in enumerate(sec["lessons"], start=1):
            # find next anchor printed page across the whole flat list
            later = [f["printed"] for f in flat if f["printed"] > printed]
            printed_end = (min(later) - 1) if later else (boundary - 1)
            if printed_end < printed:
                printed_end = printed
            raw, pstart, pend = pdf_slice(printed, printed_end)
            for pp in range(pstart, pend + 1):
                pages_covered.add(pp)

            suffix = num.split(".")[-1]
            if suffix in SPECIAL_TYPE:
                blocks = [(SPECIAL_TYPE[suffix], raw)]
            else:
                blocks = split_blocks(raw)
                if not blocks:
                    blocks = [("explanation", raw)]

            content = []
            for (ctype, chunk) in blocks:
                content.append({
                    "type": ctype,
                    "provenance": "SOURCE",
                    "text": norm(chunk)[:6000],
                    "normalized_text": norm(chunk)[:6000],
                    "original_text": chunk[:8000],
                    "page_start": pstart,
                    "page_end": pend,
                    "source_page": pstart,
                })
                n_blocks += 1

            les_id = f"{tb_id}-l{num}"
            await db.lessons.replace_one({"id": les_id}, {
                "id": les_id, "textbook_id": tb_id, "section_id": sec_id,
                "order": l_order, "number": num, "title": f"{num} {title}" if suffix.isdigit() else title,
                "page_start": pstart, "page_end": pend, "content": content,
            }, upsert=True)
            n_lessons += 1

    # Answer key — stored separately, NEVER returned by lesson endpoints
    araw, apstart, apend = pdf_slice(cfg["answers"]["printed_page"], cfg["answers"]["printed_end"])
    await db.answer_keys.replace_one({"textbook_id": tb_id}, {
        "textbook_id": tb_id, "provenance": "SOURCE", "exposed_to_student": False,
        "page_start": apstart, "page_end": apend,
        "normalized_text": norm(araw)[:12000], "original_text": araw[:16000],
    }, upsert=True)

    cov_min, cov_max = (min(pages_covered), max(pages_covered)) if pages_covered else (0, 0)
    print(f"sections={n_sections} lessons={n_lessons} blocks={n_blocks} "
          f"page_coverage={cov_min}-{cov_max} ({len(pages_covered)} pdf pages) "
          f"answers_pages={apstart}-{apend}")
    return n_sections, n_lessons, n_blocks


async def main():
    pdf = sys.argv[1] if len(sys.argv) > 1 else str(ROOT / "mathbook.pdf")
    await ingest(pdf, MATH_CONFIG)
    client.close()


if __name__ == "__main__":
    asyncio.run(main())
