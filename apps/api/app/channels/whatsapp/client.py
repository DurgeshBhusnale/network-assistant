"""WhatsApp Cloud API client (Meta, direct). Every send goes through the recipient guard.

Rule 4: the bot only messages the user's own verified number (profiles.wa_phone_e164), and only
while they are opted in. The guard looks the number up itself; callers never pass a phone.
Without WA credentials the client runs dry (logs metadata, sends nothing) for local development.
"""

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.db import service_session
from app.domain.models import Profile, WaMessage
from app.services.consents import has_consent

logger = logging.getLogger(__name__)

GRAPH = "https://graph.facebook.com"


class RecipientNotAllowedError(PermissionError):
    """Raised before any network call when the guard refuses a recipient."""


class WhatsAppError(RuntimeError):
    pass


class WhatsAppClient:
    def __init__(self, settings: Settings, engine: AsyncEngine) -> None:
        self._settings = settings
        self._engine = engine
        token = settings.wa_access_token.get_secret_value() if settings.wa_access_token else ""
        self._token = token
        self.dry_run = not (token and settings.wa_phone_number_id and settings.wa_graph_version)

    @property
    def _base(self) -> str:
        return f"{GRAPH}/{self._settings.wa_graph_version}"

    async def _recipient(self, user_id: uuid.UUID, *, allow_opted_out: bool) -> str:
        async with service_session(self._engine) as session:
            profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
            consented = await has_consent(session, user_id, "whatsapp")
        if not consented and not allow_opted_out:
            raise RecipientNotAllowedError("user withdrew WhatsApp consent")
        if profile is None or not profile.wa_phone_e164 or profile.wa_opt_in_at is None:
            raise RecipientNotAllowedError("user has no verified WhatsApp number")
        if profile.wa_opt_out_at is not None and not allow_opted_out:
            raise RecipientNotAllowedError("user opted out")
        return profile.wa_phone_e164.lstrip("+")

    async def _log(
        self, user_id: uuid.UUID, kind: str, template: str | None, wa_id: str | None
    ) -> None:
        async with service_session(self._engine) as session:
            session.add(
                WaMessage(
                    user_id=user_id,
                    direction="out",
                    kind=kind,
                    template_name=template,
                    wa_message_id=wa_id,
                    status="dry_run" if wa_id is None else "sent",
                )
            )

    async def _send(
        self,
        user_id: uuid.UUID,
        kind: str,
        body: dict[str, Any],
        *,
        template: str | None = None,
        allow_opted_out: bool = False,
    ) -> str | None:
        to = await self._recipient(user_id, allow_opted_out=allow_opted_out)
        if self.dry_run:
            logger.info("wa_dry_run", extra={"kind": kind, "template": template})
            await self._log(user_id, kind, template, None)
            return None
        payload = {"messaging_product": "whatsapp", "to": to, **body}
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(
                f"{self._base}/{self._settings.wa_phone_number_id}/messages",
                json=payload,
                headers={"Authorization": f"Bearer {self._token}"},
            )
        if r.status_code >= 300:
            logger.warning("wa_send_failed", extra={"kind": kind, "status": r.status_code})
            raise WhatsAppError(f"send failed: {r.status_code}")
        wa_id = ((r.json().get("messages") or [{}])[0]).get("id")
        await self._log(user_id, kind, template, wa_id)
        return str(wa_id) if wa_id else None

    async def send_text(
        self, user_id: uuid.UUID, text: str, *, allow_opted_out: bool = False
    ) -> None:
        await self._send(
            user_id,
            "text",
            {"type": "text", "text": {"body": text[:4096], "preview_url": True}},
            allow_opted_out=allow_opted_out,
        )

    async def send_buttons(
        self, user_id: uuid.UUID, text: str, buttons: list[tuple[str, str]]
    ) -> None:
        """Up to 3 reply buttons: (id, title ≤ 20 chars)."""
        await self._send(
            user_id,
            "interactive",
            {
                "type": "interactive",
                "interactive": {
                    "type": "button",
                    "body": {"text": text[:1024]},
                    "action": {
                        "buttons": [
                            {"type": "reply", "reply": {"id": bid[:256], "title": title[:20]}}
                            for bid, title in buttons[:3]
                        ]
                    },
                },
            },
        )

    async def send_template(
        self,
        user_id: uuid.UUID,
        name: str,
        body_params: list[str],
        quick_replies: list[str] | None = None,
    ) -> None:
        components: list[dict[str, Any]] = [
            {"type": "body", "parameters": [{"type": "text", "text": p} for p in body_params]}
        ]
        for index, payload in enumerate(quick_replies or []):
            components.append(
                {
                    "type": "button",
                    "sub_type": "quick_reply",
                    "index": str(index),
                    "parameters": [{"type": "payload", "payload": payload}],
                }
            )
        await self._send(
            user_id,
            "template",
            {
                "type": "template",
                "template": {
                    "name": name,
                    "language": {"code": self._settings.wa_template_language},
                    "components": components,
                },
            },
            template=name,
        )

    async def download_media(self, media_id: str, max_bytes: int) -> tuple[bytes, str]:
        if self.dry_run:
            raise WhatsAppError("media download unavailable in dry run")
        headers = {"Authorization": f"Bearer {self._token}"}
        async with httpx.AsyncClient(timeout=30) as client:
            meta = await client.get(f"{self._base}/{media_id}", headers=headers)
            if meta.status_code >= 300:
                raise WhatsAppError(f"media lookup failed: {meta.status_code}")
            info = meta.json()
            r = await client.get(info["url"], headers=headers)
        if r.status_code >= 300 or len(r.content) > max_bytes:
            raise WhatsAppError("media download failed")
        return r.content, str(info.get("mime_type") or "audio/ogg")


def now_utc() -> datetime:
    return datetime.now(UTC)
