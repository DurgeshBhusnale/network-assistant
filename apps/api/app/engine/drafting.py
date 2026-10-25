"""Draft rules enforced in code (tech spec §8.3, doc 05 §6). Pure."""

import re
from dataclasses import dataclass

MAX_WORDS = 90

_URL = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)
_ASK_PATTERNS = [
    r"\brefer(ral|rals|red|ring)?\b",
    r"\bopenings?\b",
    r"\bresume\b",
    r"\bcv\b",
    r"\bjob(s)?\b",
    r"\bcould you help me\b",
    r"\bcan you help me get\b",
    r"\bintroduce me\b",
    r"\brefer kar",
    r"\bjob ke liye\b",
]
_ASK = re.compile("|".join(_ASK_PATTERNS), re.IGNORECASE)

TONE_INSTRUCTIONS = {
    "shorter": "shorter: at most 40 words",
    "warmer": "warmer: more personal",
    "formal": "more formal: respectful, no slang",
    "hinglish": "write in Hinglish (Hindi words in Latin script mixed naturally with English)",
}

LANGUAGE_LINES = {
    "en": "English, in Latin script only. Never use Devanagari or any other script.",
    "hinglish": (
        "Hinglish: Hindi words written in Latin script (e.g. 'kaise ho', 'yaar', 'bahut') mixed "
        "naturally with English. Never use Devanagari."
    ),
    "hi": "Hindi, written in Devanagari script.",
    "mr": "Marathi, written in Devanagari script.",
}

LATIN_ONLY_LANGUAGES = frozenset({"en", "hinglish"})
_DEVANAGARI = re.compile("[ऀ-ॿ]")


def word_count(text: str) -> int:
    return len(text.split())


def urls_in(text: str) -> list[str]:
    return [u.rstrip(".,)") for u in _URL.findall(text)]


def ask_detected(text: str) -> bool:
    return _ASK.search(text) is not None


@dataclass(frozen=True)
class RuleCheck:
    too_long: bool
    has_ask: bool
    unexpected_urls: list[str]
    wrong_script: bool = False

    @property
    def ok(self) -> bool:
        return not (self.too_long or self.has_ask or self.unexpected_urls or self.wrong_script)

    def fix_instructions(self) -> list[str]:
        fixes = []
        if self.too_long:
            fixes.append(f"Keep it under {MAX_WORDS} words.")
        if self.has_ask:
            fixes.append("This is a warm-up: remove any request of any kind.")
        if self.unexpected_urls:
            fixes.append("Do not include any links.")
        if self.wrong_script:
            fixes.append("Write only in Latin script. Do not use Devanagari at all.")
        return fixes

    def warnings(self) -> list[str]:
        out = []
        if self.too_long:
            out.append("too_long")
        if self.has_ask:
            out.append("contains_ask")
        if self.unexpected_urls:
            out.append("unexpected_link")
        if self.wrong_script:
            out.append("wrong_script")
        return out


def check_rules(
    text: str, *, stage_has_ask: bool, allowed_urls: list[str], language: str = "en"
) -> RuleCheck:
    allowed = {u.rstrip("/").lower() for u in allowed_urls}
    return RuleCheck(
        too_long=word_count(text) > MAX_WORDS,
        has_ask=(not stage_has_ask) and ask_detected(text),
        unexpected_urls=[u for u in urls_in(text) if u.rstrip("/").lower() not in allowed],
        wrong_script=language in LATIN_ONLY_LANGUAGES and _DEVANAGARI.search(text) is not None,
    )


def job_link_for(company_norm: str | None, job_links: list[str]) -> str | None:
    """A goal job link whose URL mentions the contact's company (e.g. careers.razorpay.com)."""
    if not company_norm:
        return None
    tokens = [t for t in re.split(r"\W+", company_norm) if len(t) >= 3]
    for link in job_links:
        lowered = link.lower()
        if any(token in lowered for token in tokens):
            return link
    return None
