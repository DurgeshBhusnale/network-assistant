import io
import json
import logging

import pytest

from app.core.logging import build_handler
from app.core.redaction import FIELD_MASK, redact_text, redact_value


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("call +91 98765 43210 now", "call [phone] now"),
        ("call +919876543210", "call [phone]"),
        ("call 98765 43210", "call [phone]"),
        ("call 9876543210", "call [phone]"),
        ("call 098765-43210", "call [phone]"),
        ("call 91 98765 43210", "call [phone]"),
        ("us +1 415 555 0132", "us [phone]"),
        ("mail Rohan.K+jobs@Example.co.in please", "mail [email] please"),
        ("both a@b.io and +44 20 7946 0958", "both [email] and [phone]"),
    ],
)
def test_redact_text_masks_phones_and_emails(raw: str, expected: str) -> None:
    assert redact_text(raw) == expected


@pytest.mark.parametrize(
    "safe",
    [
        "2026-10-25 14:42:00",
        "user 3f2b8c1e-9d4a-4f6b-8e2a-1c5d7e9f0a3b",
        "latency_ms=1234",
        "order_RZP1234567",
        "goal day 12 of 60",
    ],
)
def test_redact_text_keeps_non_pii(safe: str) -> None:
    assert redact_text(safe) == safe


def test_redact_value_masks_sensitive_keys_and_nested_strings() -> None:
    value = {
        "user_id": "u1",
        "text": "Met Priya at eChai",
        "meta": {"phones": ["+919876543210"], "note_count": 3, "who": "x@y.com"},
        "items": ["ping 9876543210"],
    }

    assert redact_value(value) == {
        "user_id": "u1",
        "text": FIELD_MASK,
        "meta": {"phones": FIELD_MASK, "note_count": 3, "who": "[email]"},
        "items": ["ping [phone]"],
    }


def _capture_logger() -> tuple[logging.Logger, io.StringIO]:
    stream = io.StringIO()
    logger = logging.getLogger("test.redaction")
    logger.handlers = [build_handler(stream)]
    logger.propagate = False
    logger.setLevel(logging.INFO)
    return logger, stream


def test_log_redaction_masks_phone_and_email() -> None:
    logger, stream = _capture_logger()

    logger.info(
        "contact %s reached at %s",
        "rohan@example.com",
        "+91 98765 43210",
        extra={"transcript": "Met Priya Nair", "contact_id": "c1", "email": "p@zoho.com"},
    )

    line = json.loads(stream.getvalue())
    assert line["msg"] == "contact [email] reached at [phone]"
    assert line["transcript"] == FIELD_MASK
    assert line["email"] == FIELD_MASK
    assert line["contact_id"] == "c1"
    assert line["level"] == "INFO"
    for leaked in ("rohan@example.com", "98765", "Priya", "zoho.com"):
        assert leaked not in stream.getvalue()


def test_log_redaction_masks_exception_text() -> None:
    logger, stream = _capture_logger()

    try:
        raise ValueError("bad phone 9876543210 for a@b.io")
    except ValueError:
        logger.exception("failed")

    output = stream.getvalue()
    assert "9876543210" not in output
    assert "a@b.io" not in output
    assert "[phone]" in json.loads(output)["exc"]
