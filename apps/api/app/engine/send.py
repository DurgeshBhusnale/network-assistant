"""Send links (FR-SEND-1/2, ADR-0004): the user's own WhatsApp/LinkedIn opens with the text."""

from urllib.parse import quote

from rapidfuzz.distance import Levenshtein


def whatsapp_url(phone_e164: str, text: str) -> str:
    """`+91 98765 43210` → https://wa.me/919876543210?text=… (digits only, text URL-encoded)."""
    digits = "".join(ch for ch in phone_e164 if ch.isdigit())
    return f"https://wa.me/{digits}?text={quote(text, safe='')}"


def edit_ratio(generated: str, final: str | None) -> float:
    """Normalised Levenshtein distance between the draft and what was sent (tech spec §13)."""
    if final is None:
        return 0.0
    return round(float(Levenshtein.normalized_distance(generated, final)), 3)
