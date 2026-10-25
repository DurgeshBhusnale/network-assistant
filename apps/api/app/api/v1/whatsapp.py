"""Linking (FR-WA-1) and the Meta webhook (tech spec §9)."""

import dataclasses
import logging
import secrets
from datetime import timedelta
from urllib.parse import quote

from fastapi import APIRouter, Query, Request, Response
from pydantic import BaseModel
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert

from app.api.v1.deps import ClockDep, SettingsDep
from app.channels.whatsapp.inbound import parse_webhook, signature_valid
from app.core.auth import CurrentUser
from app.core.db import Engine, service_session, user_session
from app.core.errors import AppError, ErrorCode
from app.domain.models import Profile, WaLinkCode, WaMessage
from app.services.consents import require_consent
from app.services.profiles import ensure_profile
from app.workers.queue import enqueue

logger = logging.getLogger(__name__)
router = APIRouter(tags=["whatsapp"])

CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"  # no 0/O, 1/I


class LinkCodeOut(BaseModel):
    code: str
    wa_url: str
    expires_in_minutes: int


class WhatsAppStatus(BaseModel):
    linked: bool
    phone_hint: str | None
    opted_out: bool
    number_configured: bool


@router.post("/whatsapp/link-code", response_model=LinkCodeOut, status_code=201)
async def link_code(
    user: CurrentUser, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> LinkCodeOut:
    if not settings.wa_display_number:
        raise AppError(ErrorCode.HTTP_ERROR, "WhatsApp isn't set up yet.", 503)
    async with user_session(engine, user) as session:
        await ensure_profile(session, user)
        await require_consent(
            session, user.id, "whatsapp", "Allow WhatsApp messages in Settings → Privacy first."
        )
    minutes = settings.wa_link_code_minutes
    async with service_session(engine) as session:
        for _ in range(5):
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(6))
            inserted = await session.scalar(
                insert(WaLinkCode)
                .values(
                    code=code, user_id=user.id, expires_at=clock.now() + timedelta(minutes=minutes)
                )
                .on_conflict_do_nothing()
                .returning(WaLinkCode.code)
            )
            if inserted:
                break
        else:
            raise AppError(ErrorCode.HTTP_ERROR, "Couldn't create a code. Try again.", 503)
    text = quote(f"START {code}")
    return LinkCodeOut(
        code=code,
        wa_url=f"https://wa.me/{settings.wa_display_number}?text={text}",
        expires_in_minutes=minutes,
    )


@router.get("/whatsapp/status", response_model=WhatsAppStatus)
async def whatsapp_status(
    user: CurrentUser, engine: Engine, settings: SettingsDep
) -> WhatsAppStatus:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        phone = profile.wa_phone_e164
        return WhatsAppStatus(
            linked=phone is not None and profile.wa_opt_in_at is not None,
            phone_hint=f"••••{phone[-4:]}" if phone else None,
            opted_out=profile.wa_opt_out_at is not None,
            number_configured=bool(settings.wa_display_number),
        )


@router.delete("/whatsapp/link", status_code=204)
async def unlink(user: CurrentUser, engine: Engine) -> None:
    # Server-managed columns (ADR-0007): written with the service role, scoped to this user.
    async with service_session(engine) as session:
        await session.execute(
            update(Profile)
            .where(Profile.user_id == user.id)
            .values(wa_phone_e164=None, wa_opt_in_at=None, wa_opt_out_at=None)
        )


@router.get("/webhooks/whatsapp")
async def verify_webhook(
    settings: SettingsDep,
    mode: str = Query("", alias="hub.mode"),
    token: str = Query("", alias="hub.verify_token"),
    challenge: str = Query("", alias="hub.challenge"),
) -> Response:
    expected = settings.wa_verify_token.get_secret_value() if settings.wa_verify_token else ""
    if mode == "subscribe" and expected and secrets.compare_digest(token, expected):
        return Response(content=challenge, media_type="text/plain")
    return Response(status_code=403)


@router.post("/webhooks/whatsapp")
async def receive_webhook(request: Request, engine: Engine, settings: SettingsDep) -> Response:
    """Verify the signature, dedupe by message id, record metadata, hand off to the worker.
    Replies 200 fast; never stores message bodies."""
    raw = await request.body()
    secret = settings.wa_app_secret.get_secret_value() if settings.wa_app_secret else ""
    if not signature_valid(raw, request.headers.get("x-hub-signature-256"), secret):
        return Response(status_code=401)
    try:
        messages, statuses = parse_webhook(await request.json())
    except ValueError:
        return Response(status_code=400)

    fresh = []
    async with service_session(engine) as session:
        for m in messages:
            new_id = await session.scalar(
                insert(WaMessage)
                .values(direction="in", kind=m.kind, wa_message_id=m.id, status="received")
                .on_conflict_do_nothing(index_elements=["wa_message_id"])
                .returning(WaMessage.id)
            )
            if new_id is not None:
                fresh.append(m)
        for s in statuses:
            await session.execute(
                update(WaMessage).where(WaMessage.wa_message_id == s.id).values(status=s.status)
            )
    for m in fresh:
        await enqueue(request, "handle_whatsapp", dataclasses.asdict(m))
    if fresh and getattr(request.app.state, "queue", None) is None:
        logger.warning("wa_no_queue", extra={"dropped": len(fresh)})
    return Response(status_code=200)
