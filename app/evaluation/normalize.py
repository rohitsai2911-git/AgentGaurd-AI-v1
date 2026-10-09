from __future__ import annotations

import re
import unicodedata

STOPWORDS: frozenset[str] = frozenset(
    """
    a an the and or but if then than that this these those is are was were be been being am
    do does did doing have has had having will would shall should can could may might must
    of in on at by for with about against between into through during before after above
    below to from up down out off over under again further once here there when where why how
    all any both each few more most other some such no nor only own same so too very just
    me my we our you your he him his she her it its them their there here what which who whom
    as also very really s t don now i'm i've it's that's
    """.split()
)

COMMON_CAPS: frozenset[str] = frozenset(
    """
    i the a an my our we your you he him his she her it they them their this that these those
    if in on at to for from by with and or but so as is are was were be been will would can
    could should may might do does did have has had thank thanks hello hi dear regards please
    yes no ok okay sure unfortunately apologies what which who whom whose when where why how
    sorry unfortunately here there now today please note kindly best regards sincerely let lets
    my our your their its his her our yours thanks thank you welcome
    """.split()
)

_PUNCT_RE = re.compile(r"[^\w\s]", re.UNICODE)
_WS_RE = re.compile(r"\s+")
_SENTENCE_RE = re.compile(r"(?<=[.!?])\s+(?=[\"'(\[]?[A-Z0-9])")
_NUM_RE = re.compile(r"(?<![\w.])(\d{1,3}(?:,\d{3})+(?:\.\d+)?|\d+(?:\.\d+)?)(?![\w])")
_ENTITY_RE = re.compile(r"\b[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\b")
_WORD_RE = re.compile(r"\w+")
_RAW_TOKEN_RE = re.compile(r"\$?\d[\d,]*(?:\.\d+)?%?|[A-Za-z][A-Za-z'\-]*")
_NUMERIC_TOKEN_RE = re.compile(r"\d[\d,]*(?:\.\d+)?")

EMAIL_RE = re.compile(r"\b[\w.+-]+@[\w-]+\.[\w.-]+\b")
URL_RE = re.compile(r"\bhttps?://\S+|\bwww\.\S+", re.IGNORECASE)
PHONE_RE = re.compile(r"\b(?:\+\d{1,3}[\s-]?)?(?:\(?\d{3}\)?[\s.-]?)\d{3}[\s.-]?\d{4}\b")
CARD_RE = re.compile(r"\b(?:\d[ -]?){13,19}\b")
ORDER_REF_RE = re.compile(r"\b(?:order|reference|ref|ticket|case|invoice|id)[-_ ]?#?\s?\d{4,}\b", re.IGNORECASE)
DATE_RE = re.compile(
    r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}[/-]\d{1,2}[/-]\d{2,4}|"
    r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{1,2},?\s*\d{4})\b",
    re.IGNORECASE,
)

QUOTES = {"\u2019": "'", "\u2018": "'", "\u201c": '"', "\u201d": '"'}
DASHES = {"\u2013": "-", "\u2014": "-", "\u2212": "-", "\u2010": "-", "\u2011": "-"}


def normalize_text(text: str) -> str:
    if not text:
        return ""
    t = unicodedata.normalize("NFKD", text).lower()
    t = "".join(ch for ch in t if not unicodedata.combining(ch))
    for src, dst in QUOTES.items():
        t = t.replace(src, dst)
    for src, dst in DASHES.items():
        t = t.replace(src, dst)
    t = _PUNCT_RE.sub(" ", t)
    return _WS_RE.sub(" ", t).strip()


def tokenize(text: str, keep_stopwords: bool = False) -> list[str]:
    tokens = _WORD_RE.findall(normalize_text(text))
    if keep_stopwords:
        return tokens
    return [t for t in tokens if t not in STOPWORDS and len(t) > 1]


def token_set(text: str) -> set[str]:
    return set(tokenize(text))


def word_count(text: str) -> int:
    return len(_WORD_RE.findall(text))


def split_sentences(text: str) -> list[str]:
    if not text or not text.strip():
        return []
    parts = [p.strip() for p in _SENTENCE_RE.split(text.strip())]
    return [p for p in parts if p]


def extract_numbers(text: str) -> list[float]:
    out: list[float] = []
    for raw in _NUM_RE.findall(text or ""):
        cleaned = raw.replace(",", "")
        try:
            out.append(float(cleaned))
        except ValueError:
            continue
    return out


def extract_entities(text: str) -> list[str]:
    if not text:
        return []
    entities: list[str] = []
    for match in _ENTITY_RE.finditer(text):
        phrase = match.group(0).strip()
        prefix = text[: match.start()].rstrip()
        sentence_initial = not prefix or prefix[-1] in ".!?"
        words = phrase.split()
        if sentence_initial and len(words) == 1 and words[0].lower() in COMMON_CAPS:
            continue
        if all(w.lower() in COMMON_CAPS for w in words):
            continue
        entities.append(phrase)
    return entities


def extract_all_labeled_values(text: str) -> list[tuple[str, float]]:
    """Every ``(label, value)`` pair in order, including repeats.

    ``extract_labeled_values`` keeps only the first value per label, which is what
    callers comparing single figures want. Contradiction detection needs the repeats.
    """
    tokens = [m.group(0) for m in _RAW_TOKEN_RE.finditer(text or "")]
    lowered = [t.lower().strip("$%") for t in tokens]
    pairs: list[tuple[str, float]] = []
    for i, token in enumerate(lowered):
        if not _NUMERIC_TOKEN_RE.fullmatch(token):
            continue
        label_parts: list[str] = []
        j = i - 1
        while j >= 0 and len(label_parts) < 2:
            candidate = lowered[j]
            if candidate and candidate not in STOPWORDS:
                label_parts.insert(0, candidate)
            j -= 1
        label = " ".join(label_parts)
        if not label:
            continue
        try:
            value = float(token.replace(",", ""))
        except ValueError:
            continue
        pairs.append((label, value))
    return pairs


def extract_labeled_values(text: str) -> dict[str, float]:
    """Map a nearby label to its numeric value.

    The label is the up-to-two preceding non-stopword tokens, which keeps labels
    comparable across responses written with similar phrasing.
    """
    out: dict[str, float] = {}
    for label, value in extract_all_labeled_values(text):
        out.setdefault(label, value)
    return out


def jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 1.0
    if not a or not b:
        return 0.0
    union = a | b
    return len(a & b) / len(union)


def overlap(a: set[str], b: set[str]) -> float:
    """Overlap coefficient. Forgiving of extra words, so paraphrases score high."""
    if not a or not b:
        return 0.0
    return len(a & b) / min(len(a), len(b))


def singular(word: str) -> str:
    if len(word) > 3 and word.endswith("ies"):
        return word[:-3] + "y"
    if len(word) > 3 and word.endswith("es") and word[-3] in "sxzh":
        return word[:-2]
    if len(word) > 3 and word.endswith("s") and not word.endswith("ss"):
        return word[:-1]
    return word


def contains_phrase(text_normalized: str, phrase: str) -> bool:
    """Token-sequence match after singular normalisation.

    ``refund`` matches ``Refunds`` and ``policies`` but not ``refunded``: both sides
    are singularised and compared as a contiguous token subsequence, so word
    boundaries are still respected.
    """
    needle = [singular(token) for token in normalize_text(phrase).split()]
    if not needle:
        return False
    haystack = [singular(token) for token in text_normalized.split()]
    width = len(needle)
    return any(
        haystack[i : i + width] == needle for i in range(len(haystack) - width + 1)
    )


def truncate(text: str, limit: int = 160) -> str:
    text = " ".join((text or "").split())
    return text if len(text) <= limit else text[: limit - 1] + "\u2026"