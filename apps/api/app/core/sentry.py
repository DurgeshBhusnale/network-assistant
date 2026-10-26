"""Sentry setup: a no-op without a DSN; never sends request bodies or PII."""

from typing import Any

import sentry_sdk

from app.core.config import Settings
from app.core.redaction import redact_value

_DROPPED_REQUEST_KEYS = ("data", "cookies", "query_string")
_DROPPED_HEADERS = frozenset(
    {"authorization", "cookie", "x-hub-signature-256", "x-razorpay-signature"}
)


def scrub_event(event: dict[str, Any], _hint: dict[str, Any]) -> dict[str, Any]:
    request = event.get("request")
    if isinstance(request, dict):
        for key in _DROPPED_REQUEST_KEYS:
            request.pop(key, None)
        headers = request.get("headers")
        if isinstance(headers, dict):
            request["headers"] = {
                k: v for k, v in headers.items() if k.lower() not in _DROPPED_HEADERS
            }
    scrubbed: dict[str, Any] = redact_value(event)
    return scrubbed


def init_sentry(settings: Settings) -> bool:
    if settings.sentry_dsn is None or not settings.sentry_dsn.get_secret_value():
        return False
    sentry_sdk.init(
        dsn=settings.sentry_dsn.get_secret_value(),
        environment=settings.app_env,
        send_default_pii=False,
        max_request_body_size="never",
        before_send=scrub_event,  # type: ignore[arg-type]
        traces_sample_rate=0.0,
    )
    return True
