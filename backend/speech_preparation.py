"""Conservative speech preparation for Azerbaijani math text.

Only the confirmed simple fraction 3/4, including same-line horizontal
spacing such as 3 / 4, is converted. Other fractions remain unchanged.
"""

import re
from typing import Any, Optional


_MATH_SUBJECTS = {"riyaziyyat", "math", "mathematics"}
_MATH_TOPIC_MARKERS = (
    "ədəd",
    "hesab",
    "əməl",
    "vur",
    "böl",
    "kəsr",
    "kesr",
    "faiz",
    "cəbr",
    "cebr",
    "tənlik",
    "tenlik",
    "math",
    "number",
    "arithmetic",
    "fraction",
    "multipli",
    "divis",
    "percent",
    "algebra",
    "equation",
)
_FRACTION_TOPIC_MARKERS = ("kəsr", "kesr", "fraction")
_PERCENT_TOPIC_MARKERS = ("faiz", "percent", "percentage")
_ALGEBRA_TOPIC_MARKERS = ("cəbr", "cebr", "algebra", "tənlik", "tenlik", "equation")

_IDENTIFIER_CHARS = r"A-Za-z0-9_ƏəÇçĞğİıÖöŞşÜü"

# Protect common special spans before processing ordinary text. This is a
# narrow safety net, not a complete parser for every URL, date, or identifier.
_PROTECTED_RE = re.compile(
    r"(?P<fenced_code>```[\s\S]*?(?:```|\Z))"
    r"|(?P<inline_code>`[^`\n]*`)"
    r"|(?P<url>\b(?:https?://|www\.)[^\s<>()]+)"
    r"|(?P<email>\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b)"
    r"|(?P<date>(?<![\w./-])\d{1,4}[ \t]*[./-][ \t]*\d{1,2}[ \t]*[./-][ \t]*\d{1,4}(?![\w./-]))"
    r"|(?P<time>(?<![\w:])\d{1,2}:\d{2}(?::\d{2})?(?![\w:]))"
    r"|(?P<version>(?<![\w.])[vV]?\d+(?:\.\d+){2,}(?![\w.]))"
    rf"|(?P<identifier>(?<![{_IDENTIFIER_CHARS}])"
    rf"(?:[A-Za-zƏəÇçĞğİıÖöŞşÜü][A-Za-z0-9ƏəÇçĞğİıÖöŞşÜü]*[_-][A-Za-z0-9_ƏəÇçĞğİıÖöŞşÜü-]*"
    rf"|[A-Za-zƏəÇçĞğİıÖöŞşÜü]+\d+[A-Za-z0-9_ƏəÇçĞğİıÖöŞşÜü-]*)"
    rf"(?![{_IDENTIFIER_CHARS}]))"
    r"|(?P<decimal>(?<![\w.])[+-]?\d+[.,]\d+(?![\w.]))"
    r"|(?P<negative_number>(?<!\w)-\d+(?!\w))"
    r"|(?P<slash_number>(?<![\w./])\d+[ \t]*/[ \t]*\d+(?![\w/]|[ \t]*/))",
    re.IGNORECASE,
)

_MULTIPLICATION_RE = re.compile(
    r"(?<![\w.,])(\d+)[ \t]*×[ \t]*(\d+)(?![\w.,])"
)
_DIVISION_RE = re.compile(
    r"(?<![\w.,])(\d+)[ \t]*÷[ \t]*(\d+)(?![\w.,])"
)
_STANDALONE_PERCENT_RE = re.compile(r"[ \t]*(\d+)%[ \t]*")
_STANDALONE_EQUATION_RE = re.compile(r"[ \t]*x[ \t]*=[ \t]*5[ \t]*([.!?]?)[ \t]*")


def _topic_matches(topic: Optional[str], markers: tuple[str, ...]) -> bool:
    if not isinstance(topic, str):
        return False
    normalized = topic.casefold()
    return any(marker in normalized for marker in markers)


def _prepare_unprotected_text(text: str, *, allow_fraction: bool) -> str:
    if allow_fraction:
        text = re.sub(
            r"(?<![\w./])3[ \t]*/[ \t]*4(?![\w/]|[ \t]*/)",
            "dörddə üç",
            text,
        )
    text = _MULTIPLICATION_RE.sub(r"\1 vur \2", text)
    return _DIVISION_RE.sub(r"\1 böl \2", text)


def prepare_speech_text(
    text: Any,
    *,
    lang: str,
    subject: Optional[str] = None,
    topic: Optional[str] = None,
    fraction_confirmed: bool = False,
) -> Any:
    """Return separate speech text without changing the supplied source text.

    Transformations require lang="az", a recognized math subject, and a
    recognized math topic. Fractions additionally require a fraction-related
    topic and fraction_confirmed=True; only 3/4 (also written 3 / 4 on one
    line) is converted. Other fractions remain unchanged. Percentages and the
    supported equation are transformed only as standalone expressions in
    relevant topics. Recognized code, URL, date, time, decimal, and
    number-slash spans are kept out of math transformations.
    """
    if not isinstance(text, str) or lang != "az":
        return text
    if not isinstance(subject, str) or subject.strip().casefold() not in _MATH_SUBJECTS:
        return text
    if not _topic_matches(topic, _MATH_TOPIC_MARKERS):
        return text

    fraction_context = _topic_matches(topic, _FRACTION_TOPIC_MARKERS)
    percent_context = _topic_matches(topic, _PERCENT_TOPIC_MARKERS)
    algebra_context = _topic_matches(topic, _ALGEBRA_TOPIC_MARKERS)

    if percent_context:
        match = _STANDALONE_PERCENT_RE.fullmatch(text)
        if match:
            return f"{match.group(1)} faiz"

    if algebra_context:
        match = _STANDALONE_EQUATION_RE.fullmatch(text)
        if match:
            return f"x bərabərdir 5{match.group(1)}"

    allow_fraction = fraction_confirmed is True and fraction_context
    output: list[str] = []
    position = 0

    for match in _PROTECTED_RE.finditer(text):
        output.append(
            _prepare_unprotected_text(
                text[position:match.start()],
                allow_fraction=allow_fraction,
            )
        )

        is_confirmed_fraction = (
            allow_fraction
            and match.lastgroup == "slash_number"
            and re.sub(r"[ \t]+", "", match.group(0)) == "3/4"
        )
        output.append("dörddə üç" if is_confirmed_fraction else match.group(0))
        position = match.end()

    output.append(
        _prepare_unprotected_text(
            text[position:],
            allow_fraction=allow_fraction,
        )
    )
    return "".join(output)
