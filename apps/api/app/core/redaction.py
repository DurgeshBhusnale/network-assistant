"""PII redaction shared by logging, Sentry and (from Sprint 3) the AI prompt scrubber.

Pure functions, no I/O. Phones, emails and free text never reach logs or error reports.
"""

import re
from collections.abc import Mapping
from typing import Any

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9-]+(?:\.[A-Za-z0-9-]+)*\.[A-Za-z]{2,}")

# International numbers written with a leading "+", or Indian mobiles with an optional
# +91 / 91 / 0 prefix (e.g. "98765 43210", "098765-43210", "+91 98765 43210").
PHONE_RE = re.compile(
    r"(?<![\w+])(?:"
    r"\+\d[\d\s().-]{6,18}\d"
    r"|(?:(?:91|0)[\s-]?)?[6-9]\d{4}[\s-]?\d{5}"
    r")(?!\w)"
)

EMAIL_MASK = "[email]"
PHONE_MASK = "[phone]"
FIELD_MASK = "[redacted]"

# Keys whose values are free text or contact identifiers: always masked whole.
SENSITIVE_KEYS = frozenset(
    {
        "body",
        "content",
        "email",
        "emails",
        "final_text",
        "message",
        "message_text",
        "note",
        "phone",
        "phones",
        "samples",
        "text",
        "transcript",
        "wa_phone_e164",
    }
)


def redact_text(value: str) -> str:
    """Mask emails and phone numbers inside a string."""
    return PHONE_RE.sub(PHONE_MASK, EMAIL_RE.sub(EMAIL_MASK, value))


def redact_value(value: Any, key: str | None = None) -> Any:
    """Redact a structured value: sensitive keys are masked, strings are pattern-redacted."""
    if key is not None and key.lower() in SENSITIVE_KEYS:
        return FIELD_MASK
    if isinstance(value, str):
        return redact_text(value)
    if isinstance(value, Mapping):
        return {k: redact_value(v, str(k)) for k, v in value.items()}
    if isinstance(value, list | tuple | set):
        return [redact_value(v) for v in value]
    return value
