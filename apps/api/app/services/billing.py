"""Plan lookup and usage counts feeding billing/limits.py."""

import uuid
from datetime import datetime, time, timedelta
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.billing.limits import Limits, Plan
from app.core.config import Settings
from app.domain.models import Draft, Entitlement

CLOCK_SKEW = timedelta(minutes=2)


def limits_from(settings: Settings) -> Limits:
    return Limits(
        free_drafts_per_month=settings.free_drafts_per_month,
        free_regenerations_per_draft=settings.free_regenerations_per_draft,
        sprint_fair_use_drafts=settings.sprint_fair_use_drafts,
    )


async def active_entitlement(
    session: AsyncSession, user_id: uuid.UUID, now: datetime
) -> Entitlement | None:
    found: Entitlement | None = await session.scalar(
        select(Entitlement)
        .where(
            Entitlement.user_id == user_id,
            # Tolerate small clock differences between app servers and the database.
            Entitlement.starts_at <= now + CLOCK_SKEW,
            Entitlement.ends_at > now,
        )
        .order_by(Entitlement.ends_at.desc())
        .limit(1)
    )
    return found


async def current_plan(session: AsyncSession, user_id: uuid.UUID, now: datetime) -> Plan:
    ent = await active_entitlement(session, user_id, now)
    if ent is None:
        return Plan(kind="free")
    return Plan(kind="sprint" if ent.product == "sprint" else "pro", drafts_used=ent.drafts_used)


def month_start(now: datetime, timezone: str) -> datetime:
    """Start of the user's current calendar month, as an aware datetime."""
    local = now.astimezone(ZoneInfo(timezone))
    return datetime.combine(local.date().replace(day=1), time.min, tzinfo=local.tzinfo)


async def drafts_this_month(
    session: AsyncSession, user_id: uuid.UUID, now: datetime, timezone: str
) -> int:
    count = await session.scalar(
        select(func.count(Draft.id)).where(
            Draft.user_id == user_id, Draft.created_at >= month_start(now, timezone)
        )
    )
    return int(count or 0)
