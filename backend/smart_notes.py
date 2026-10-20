"""Smart Notes: sıfır xərcli, tam ekstraktiv dərs qeydləri mühərriki.

Yalnız Python standart kitabxanasından istifadə olunur. Heç bir LLM/xarici
xidmət çağırılmır və heç bir məlumat bazasına yazılmır: funksiya söhbətdəki
müəllim (assistant) mesajlarından cümlələri olduğu kimi seçib qruplaşdırır.
"""

import re
from collections import Counter

MAX_MESSAGES = 100
MAX_CONTENT_CHARS = 8000

# --- Markdown təmizliyi (riyazi ifadələrə toxunmur) ---
# Sətrin əvvəlindəki siyahı/başlıq işarələri: "- ", "* ", "+ ", "# ", "1. ", "2) ".
# Mütləq ardınca boşluq tələb olunur, buna görə "-3/4", "0.5", "3/4" dəyişmir.
_LINE_PREFIX_RE = re.compile(r"^[ \t]*(?:[-*+•][ \t]+|#{1,6}[ \t]+|\d{1,3}[.)][ \t]+)")
_BOLD_RE = re.compile(r"\*\*|__")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])[ \t]+")
_HAS_LETTER_RE = re.compile(r"[^\W\d_]")
_WS_RE = re.compile(r"[ \t]+")

# --- Məzmun nümunələri (xətti mürəkkəblik: (.+) + .strip(), ReDoS yoxdur) ---
_DEFINITION_RE = re.compile(r"^(?:tərif|definition)[ \t]*:[ \t]*(.+)", re.IGNORECASE)
_RULE_RE = re.compile(r"^(?:qayda|rule)[ \t]*:[ \t]*(.+)", re.IGNORECASE)
_FORMULA_LABEL_RE = re.compile(r"^(?:düstur|formula)[ \t]*:[ \t]*(.+)", re.IGNORECASE)
_DEFINITION_VERB_RE = re.compile(r"(?<!\w)(?:deyilir|adlanır|is called|is defined as)(?!\w)", re.IGNORECASE)
_FORMULA_RE = re.compile(r"[\w)\]]\s*[=≤≥<>]\s*[\w(\[−-]")

# Azərbaycan markerləri şəkilçilərlə də tutulur (imtahanda, düsturu, qaydanı, vacibdir);
# ingilis "exam"/"test" isə ciddi söz sərhədi ilə.
_AZ_MARKER_RE = re.compile(r"(?<!\w)(?:imtahan|sınaq|düstur|qayda|diqqət|vacib|qeyd|tərif)\w*", re.IGNORECASE)
_EN_MARKER_RE = re.compile(r"\b(?:exam|test)\b", re.IGNORECASE)
_EXAM_RE = re.compile(r"(?<!\w)(?:imtahan|sınaq)\w*|\b(?:exam|test)\b", re.IGNORECASE)

_WORD_RE = re.compile(r"[^\W\d_]{4,}")

_STOPWORDS = {
    "az": {
        "bunu", "buna", "bunlar", "onun", "onlar", "onları", "sənin", "mənim", "bizim",
        "hansı", "necə", "nədir", "niyə", "çünki", "amma", "lakin", "yəni", "əgər",
        "sonra", "əvvəl", "indi", "həmin", "belə", "daha", "çox", "olur", "olan",
        "olaraq", "edir", "edək", "edirik", "deyil", "kimi", "üçün", "ilə", "isə",
        "hələ", "artıq", "bəli", "xeyr", "gəl", "gəlin", "baxaq", "bilirsən", "sual",
        "cavab", "yaxşı", "əla", "düzdür", "bəs", "hər", "bütün", "biri", "ikisi",
        "burada", "orada", "şagird", "müəllim", "dərs", "dərsi", "bugün", "bizə",
    },
    "en": {
        "this", "that", "these", "those", "with", "from", "have", "your", "what",
        "when", "where", "which", "there", "their", "about", "would", "could",
        "should", "then", "than", "they", "them", "will", "just", "very", "good",
        "great", "let's", "lets", "into", "also", "because", "answer", "question",
    },
}


def _match_text(text: str) -> str:
    """Böyük hərf variantlarını regex üçün sabitləşdirir (İ→i)."""
    return text.replace("İ", "i")


def has_marker(text: str) -> bool:
    t = _match_text(text)
    return bool(_AZ_MARKER_RE.search(t) or _EN_MARKER_RE.search(t))


def clean_markdown_line(line: str) -> str:
    line = _LINE_PREFIX_RE.sub("", line, count=1)
    line = _BOLD_RE.sub("", line)
    return _WS_RE.sub(" ", line).strip()


def split_sentences(text: str) -> list:
    """Markdown-u təmizləyir, sonra cümlələrə bölür. Hərfsiz parçalar ("1.") atılır."""
    sentences = []
    for raw_line in text.splitlines():
        if not raw_line.strip():
            continue
        line = clean_markdown_line(raw_line)
        for part in _SENTENCE_SPLIT_RE.split(line):
            part = part.strip()
            if len(part) >= 3 and _HAS_LETTER_RE.search(part):
                sentences.append(part)
    return sentences


def _norm_lang(lang) -> str:
    return lang if lang in ("az", "en") else "az"


def _get(msg, key):
    if isinstance(msg, dict):
        return msg.get(key)
    return getattr(msg, key, None)


def _add_unique(bucket: list, seen: set, text: str, limit: int):
    key = text.casefold()
    if text and key not in seen and len(bucket) < limit:
        seen.add(key)
        bucket.append(text)


def generate_smart_notes(conversation, subject=None, topic=None, lang="az", exam_mode=False) -> dict:
    """Söhbətdən ekstraktiv qeydlər çıxarır. Yalnız 'assistant' mesajları nəzərə alınır."""
    lang = _norm_lang(lang)
    conversation = list(conversation or [])[-MAX_MESSAGES:]

    sentences = []
    used_messages = 0
    for msg in conversation:
        if _get(msg, "role") != "assistant":
            continue
        content = _get(msg, "content")
        if not isinstance(content, str) or not content.strip():
            continue
        used_messages += 1
        sentences.extend(split_sentences(content[:MAX_CONTENT_CHARS]))

    tip_limit = 10 if exam_mode else 5
    notes = {
        "title": topic or subject or "Dərs qeydləri",
        "subject": subject or "",
        "topic": topic or "",
        "lang": lang,
        "exam_mode": bool(exam_mode),
        "summary": [],
        "key_concepts": [],
        "definitions": [],
        "rules": [],
        "formulas": [],
        "exam_tips": [],
        "vocabulary": [],
        "source_message_count": used_messages,
    }
    seen = {k: set() for k in ("summary", "definitions", "rules", "formulas", "exam_tips")}

    marked = []
    for s in sentences:
        m = _match_text(s)
        d = _DEFINITION_RE.match(m)
        r = _RULE_RE.match(m)
        f = _FORMULA_LABEL_RE.match(m)
        if d:
            _add_unique(notes["definitions"], seen["definitions"], s[d.start(1):].strip(), 15)
        elif _DEFINITION_VERB_RE.search(m):
            _add_unique(notes["definitions"], seen["definitions"], s, 15)
        if r:
            _add_unique(notes["rules"], seen["rules"], s[r.start(1):].strip(), 15)
        if f:
            _add_unique(notes["formulas"], seen["formulas"], s[f.start(1):].strip(), 15)
        elif _FORMULA_RE.search(s):
            _add_unique(notes["formulas"], seen["formulas"], s, 15)
        if _EXAM_RE.search(m):
            _add_unique(notes["exam_tips"], seen["exam_tips"], s, tip_limit)
        if has_marker(s):
            marked.append(s)

    # Xülasə: əvvəlcə markerli cümlələr, sonra ilk cümlələr.
    for s in marked + sentences:
        if s.endswith("?"):
            continue
        _add_unique(notes["summary"], seen["summary"], s, 5)

    # Əsas anlayışlar: mövzu + ən çox təkrarlanan mənalı sözlər.
    stop = _STOPWORDS[lang]
    counts = Counter()
    display = {}
    for s in sentences:
        for w in _WORD_RE.findall(s):
            key = _match_text(w).lower()
            if key in stop:
                continue
            counts[key] += 1
            display.setdefault(key, w.lower())
    concepts = [topic] if topic else []
    concept_keys = {c.casefold() for c in concepts}
    for key, n in counts.most_common():
        if len(concepts) >= 8:
            break
        if n < 2 or key in concept_keys:
            continue
        concept_keys.add(key)
        concepts.append(display[key])
    notes["key_concepts"] = concepts
    return notes
