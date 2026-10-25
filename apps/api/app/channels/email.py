"""Email via Resend (FR-NOT-2). Dry run without a key. Bodies are never logged."""

import logging

import httpx

from app.core.config import Settings

logger = logging.getLogger(__name__)


async def send_email(
    settings: Settings, *, to: str, subject: str, html: str, text: str, unsubscribe_url: str | None
) -> bool:
    key = settings.resend_api_key.get_secret_value() if settings.resend_api_key else ""
    if not key or not settings.email_from:
        logger.info("email_dry_run")
        return False
    headers = {}
    if unsubscribe_url:
        headers = {
            "List-Unsubscribe": f"<{unsubscribe_url}>",
            "List-Unsubscribe-Post": "List-Unsubscribe=One-Click",
        }
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(
            "https://api.resend.com/emails",
            headers={"Authorization": f"Bearer {key}"},
            json={
                "from": settings.email_from,
                "to": [to],
                "subject": subject,
                "html": html,
                "text": text,
                "headers": headers,
            },
        )
    if r.status_code >= 300:
        logger.warning("email_failed", extra={"status": r.status_code})
        return False
    return True
