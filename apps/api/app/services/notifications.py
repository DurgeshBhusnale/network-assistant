"""Nudges and digests (FR-NOT-1/2, FR-TODAY-4).

Paid: a daily push at the nudge time, unless the WhatsApp brief already went out today.
Free: one weekly digest (Monday 09:00 local by default) by push and email. No WhatsApp for free.
Each send is deduplicated with a Redis key per user and day/week.
"""

import hashlib
import hmac
import html
import logging
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from redis.asyncio import Redis
from sqlalchemy import delete, select, text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.channels.email import send_email
from app.channels.push import PushGone, send_push
from app.channels.whatsapp.handler import DAILY_BRIEF, today_list
from app.core.config import Settings
from app.core.db import service_session
from app.domain.models import Profile, PushSubscription, WaMessage
from app.services import billing

logger = logging.getLogger(__name__)


def unsubscribe_token(settings: Settings, user_id: uuid.UUID) -> str:
    secret = settings.unsubscribe_secret.get_secret_value() if settings.unsubscribe_secret else ""
    return hmac.new(secret.encode(), f"digest:{user_id}".encode(), hashlib.sha256).hexdigest()[:32]


def unsubscribe_valid(settings: Settings, user_id: uuid.UUID, token: str) -> bool:
    if not settings.unsubscribe_secret:
        return False
    return hmac.compare_digest(unsubscribe_token(settings, user_id), token)


def unsubscribe_url(settings: Settings, user_id: uuid.UUID) -> str:
    token = unsubscribe_token(settings, user_id)
    return f"{settings.api_base_url}/v1/email/unsubscribe?u={user_id}&t={token}"


async def _once(redis: Redis, key: str, days: int) -> bool:
    """True the first time a key is claimed within the window."""
    claimed = await redis.set(key, "1", nx=True, ex=days * 86400)
    return bool(claimed)


async def _push_all(
    engine: AsyncEngine, settings: Settings, user_id: uuid.UUID, payload: dict[str, Any]
) -> int:
    async with service_session(engine) as session:
        subs = list(
            await session.scalars(
                select(PushSubscription).where(PushSubscription.user_id == user_id)
            )
        )
    sent = 0
    for sub in subs:
        try:
            await send_push(settings, sub.endpoint, sub.keys, payload)
            sent += 1
        except PushGone:
            async with service_session(engine) as session:
                await session.execute(
                    delete(PushSubscription).where(
                        PushSubscription.id == sub.id, PushSubscription.user_id == user_id
                    )
                )
    return sent


def _lines(items: list[Any]) -> list[str]:
    out = []
    for s, c in items[:3]:
        reason = next((r["text"] for r in s.reasons if isinstance(r, dict) and r.get("text")), None)
        out.append(f"{c.full_name} — {reason}" if reason else c.full_name)
    return out


async def _email_of(engine: AsyncEngine, user_id: uuid.UUID) -> str | None:
    async with service_session(engine) as session:
        email = await session.scalar(
            text("select email from auth.users where id = :u"), {"u": user_id}
        )
    return str(email) if email else None


async def _weekly_email(
    engine: AsyncEngine, settings: Settings, p: Profile, lines: list[str]
) -> None:
    to = await _email_of(engine, p.user_id)
    if not to:
        return
    url = unsubscribe_url(settings, p.user_id)
    app = f"{settings.app_base_url}/today"
    name = (p.display_name or "").split(" ")[0] or "there"
    items_html = "".join(f"<li>{html.escape(line)}</li>" for line in lines)
    await send_email(
        settings,
        to=to,
        subject="Your people for this week",
        html=(
            f"<p>Hi {html.escape(name)},</p>"
            f"<p>Here's who to reach out to this week:</p><ul>{items_html}</ul>"
            f'<p><a href="{app}">Open your list</a></p>'
            '<p style="color:#5B6270;font-size:12px">No more weekly emails? '
            f'<a href="{url}">Unsubscribe</a></p>'
        ),
        text=f"Hi {name},\n\nWho to reach out to this week:\n"
        + "\n".join(f"- {line}" for line in lines)
        + f"\n\nOpen your list: {app}\n\nUnsubscribe: {url}\n",
        unsubscribe_url=url,
    )


async def notify_due(
    engine: AsyncEngine, redis: Redis, settings: Settings, now: datetime
) -> dict[str, int]:
    counts = {"daily": 0, "weekly": 0}
    async with service_session(engine) as session:
        profiles = list(
            await session.scalars(select(Profile).where(Profile.onboarding_step == "done"))
        )
    for p in profiles:
        local = now.astimezone(ZoneInfo(p.timezone))
        try:
            async with service_session(engine) as session:
                plan = await billing.current_plan(session, p.user_id, now)
            if plan.kind == "free":
                if await _weekly_due(engine, redis, settings, p, local):
                    counts["weekly"] += 1
            elif await _daily_due(engine, redis, settings, p, local):
                counts["daily"] += 1
        except Exception as exc:
            logger.warning("notify_failed", extra={"error_type": type(exc).__name__})
    return counts


async def _daily_due(
    engine: AsyncEngine, redis: Redis, settings: Settings, p: Profile, local: datetime
) -> bool:
    nudge = datetime.combine(local.date(), p.nudge_time, tzinfo=local.tzinfo)
    if not (nudge <= local < nudge + timedelta(minutes=15)):
        return False
    day_start = datetime.combine(local.date(), time.min, tzinfo=local.tzinfo)
    async with service_session(engine) as session:
        briefed = await session.scalar(
            select(WaMessage.id).where(
                WaMessage.user_id == p.user_id,
                WaMessage.template_name == DAILY_BRIEF,
                WaMessage.created_at >= day_start,
            )
        )
    if briefed is not None or not await _once(redis, f"notify:daily:{p.user_id}:{local.date()}", 2):
        return False
    items = await today_list(engine, p.user_id, p.timezone)
    if not items:
        return False
    n = len(items)
    await _push_all(
        engine,
        settings,
        p.user_id,
        {
            "title": f"{n} {'person' if n == 1 else 'people'} for today",
            "body": "; ".join(_lines(items)),
            "url": "/today",
        },
    )
    return True


async def _weekly_due(
    engine: AsyncEngine, redis: Redis, settings: Settings, p: Profile, local: datetime
) -> bool:
    if (
        local.weekday() != settings.digest_weekday
        or local.hour != settings.digest_hour
        or local.minute >= 15
    ):
        return False
    week: date = local.date() - timedelta(days=local.weekday())
    if not await _once(redis, f"notify:weekly:{p.user_id}:{week}", 8):
        return False
    items = await today_list(engine, p.user_id, p.timezone)
    if not items:
        return False
    lines = _lines(items)
    await _push_all(
        engine,
        settings,
        p.user_id,
        {"title": "Your people for this week", "body": "; ".join(lines), "url": "/today"},
    )
    if p.email_digest:
        await _weekly_email(engine, settings, p, lines)
    return True
