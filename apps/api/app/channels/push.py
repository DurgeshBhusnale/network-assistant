"""Web push (VAPID) for the installed PWA (FR-NOT-1). Names and reasons only: no phones/emails."""

import json
import logging
from typing import Any

import anyio
from pywebpush import WebPushException, webpush

from app.core.config import Settings

logger = logging.getLogger(__name__)


class PushGone(Exception):
    """The browser dropped this subscription; delete it."""


def push_configured(settings: Settings) -> bool:
    return bool(settings.vapid_public_key and settings.vapid_private_key and settings.vapid_subject)


async def send_push(
    settings: Settings, endpoint: str, keys: dict[str, Any], payload: dict[str, Any]
) -> None:
    if not push_configured(settings):
        logger.info("push_dry_run")
        return
    private_key = (
        settings.vapid_private_key.get_secret_value() if settings.vapid_private_key else ""
    )

    def _send() -> None:
        webpush(
            subscription_info={"endpoint": endpoint, "keys": keys},
            data=json.dumps(payload),
            vapid_private_key=private_key,
            vapid_claims={"sub": settings.vapid_subject},
            ttl=12 * 3600,
        )

    try:
        await anyio.to_thread.run_sync(_send)
    except WebPushException as exc:
        status = getattr(exc.response, "status_code", None)
        if status in (404, 410):
            raise PushGone from exc
        logger.warning("push_failed", extra={"status": status})
