"""Normalisers for names, phones, emails, LinkedIn URLs and companies. Pure."""

import re
from urllib.parse import unquote, urlparse

import phonenumbers

DEFAULT_REGION = "IN"

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_SPACES = re.compile(r"\s+")
_COMPANY_SUFFIXES = re.compile(
    r"\b(private limited|pvt\.? ?ltd\.?|pvt|ltd\.?|limited|inc\.?|llp|llc|corp\.?|corporation"
    r"|co\.?)\s*$"
)
_PUNCT = re.compile(r"[^\w\s&]")


def clean_text(value: str | None) -> str | None:
    if value is None:
        return None
    cleaned = _SPACES.sub(" ", value).strip()
    return cleaned or None


def _smart_case(name: str) -> str:
    """Per word: title-case ALL CAPS or all-lower words; keep deliberate casing ('McDonald')."""
    return " ".join(
        w[:1].upper() + w[1:].lower() if (w.isupper() or w.islower()) else w
        for w in name.split(" ")
    )


def split_name(
    full: str | None, first: str | None = None, last: str | None = None
) -> tuple[str, str | None, str | None] | None:
    """Returns (full_name, first_name, last_name), or None when there is no usable name."""
    first_c, last_c = clean_text(first), clean_text(last)
    full_c = clean_text(full) or clean_text(" ".join(p for p in (first_c, last_c) if p))
    if not full_c:
        return None
    full_c = _smart_case(full_c)
    if first_c is None and last_c is None:
        parts = full_c.split(" ")
        first_c = parts[0]
        last_c = " ".join(parts[1:]) or None
    else:
        first_c = _smart_case(first_c) if first_c else None
        last_c = _smart_case(last_c) if last_c else None
    return full_c, first_c, last_c


def normalise_phone(raw: str | None, region: str = DEFAULT_REGION) -> str | None:
    """E.164, or None if not a valid number."""
    if not raw:
        return None
    try:
        number = phonenumbers.parse(raw, region)
    except phonenumbers.NumberParseException:
        return None
    if not phonenumbers.is_valid_number(number):
        return None
    return phonenumbers.format_number(number, phonenumbers.PhoneNumberFormat.E164)


def normalise_email(raw: str | None) -> str | None:
    if not raw:
        return None
    value = raw.strip().lower()
    if value.startswith("mailto:"):
        value = value[len("mailto:") :]
    return value if _EMAIL_RE.match(value) else None


def normalise_linkedin(raw: str | None) -> str | None:
    """https://www.linkedin.com/in/<slug>, or None if not a profile URL."""
    if not raw:
        return None
    value = raw.strip()
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    host = (parsed.hostname or "").lower()
    if not (host == "linkedin.com" or host.endswith(".linkedin.com")):
        return None
    parts = [p for p in parsed.path.split("/") if p]
    if len(parts) < 2 or parts[0].lower() != "in":
        return None
    slug = unquote(parts[1]).strip().lower()
    return f"https://www.linkedin.com/in/{slug}" if slug else None


def normalise_company(raw: str | None) -> str | None:
    """Lower-case key for matching ('Razorpay Software Pvt. Ltd.' -> 'razorpay software')."""
    value = clean_text(raw)
    if not value:
        return None
    value = value.lower()
    previous = None
    while previous != value:
        previous = value
        value = _COMPANY_SUFFIXES.sub("", value).strip(" ,.-")
    value = _SPACES.sub(" ", _PUNCT.sub(" ", value)).strip()
    return value or None


def unique(values: list[str | None]) -> list[str]:
    seen: list[str] = []
    for v in values:
        if v and v not in seen:
            seen.append(v)
    return seen
