"""Payments and entitlements (FR-PAY-1/4/5). Entitlements are granted ONLY from verified webhook
events (or the local dev simulator), idempotently by event id; refunds end the entitlement."""

import logging
import uuid
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.billing.products import Product, ProductCode, catalogue, entitlement_window
from app.core.config import Settings
from app.core.db import service_session
from app.domain.models import Entitlement, Payment
from app.domain.schemas import EntitlementOut
from app.services import billing

logger = logging.getLogger(__name__)


def products(settings: Settings) -> dict[ProductCode, Product]:
    return catalogue(
        sprint_paise=settings.price_sprint_paise,
        sprint_days=settings.sprint_days,
        pro_monthly_paise=settings.price_pro_monthly_paise,
        pro_yearly_paise=settings.price_pro_yearly_paise,
        pro_monthly_days=settings.pro_monthly_days,
        pro_yearly_days=settings.pro_yearly_days,
        pro_enabled=settings.pro_enabled,
    )


async def entitlement_out(
    session: AsyncSession, user_id: uuid.UUID, now: datetime, timezone: str, settings: Settings
) -> EntitlementOut:
    ent = await billing.active_entitlement(session, user_id, now)
    if ent is None:
        used = await billing.drafts_this_month(session, user_id, now, timezone)
        return EntitlementOut(
            plan="free",
            ends_at=None,
            days_left=None,
            drafts_used=used,
            fair_use_drafts=None,
            free_drafts_left=max(0, settings.free_drafts_per_month - used),
        )
    # Show the end of the whole paid run (chained purchases).
    last_end = await session.scalar(
        select(Entitlement.ends_at)
        .where(Entitlement.user_id == user_id, Entitlement.ends_at > now)
        .order_by(Entitlement.ends_at.desc())
        .limit(1)
    )
    ends = last_end or ent.ends_at
    sprint = ent.product == "sprint"
    return EntitlementOut(
        plan="sprint" if sprint else "pro",
        ends_at=ends,
        days_left=max(0, (ends - now).days),
        drafts_used=ent.drafts_used,
        fair_use_drafts=settings.sprint_fair_use_drafts if sprint else None,
        free_drafts_left=None,
    )


async def grant_from_event(
    engine: AsyncEngine,
    settings: Settings,
    *,
    event_id: str,
    order_id: str,
    payment_id: str | None,
    now: datetime,
) -> bool:
    """Marks the payment paid and creates/extends the entitlement. Returns False if nothing to do
    (unknown order, or this event/payment was already applied)."""
    try:
        return await _grant(engine, settings, event_id, order_id, payment_id, now)
    except IntegrityError:
        logger.warning("payment_grant_conflict")  # e.g. a payment id already recorded
        return False


async def _grant(
    engine: AsyncEngine,
    settings: Settings,
    event_id: str,
    order_id: str,
    payment_id: str | None,
    now: datetime,
) -> bool:
    async with service_session(engine) as session:
        payment = await session.scalar(
            select(Payment).where(Payment.provider_order_id == order_id).with_for_update()
        )
        if payment is None or payment.user_id is None:
            return False
        if payment.status == "paid":
            return False  # duplicate event (payment.captured and order.paid both arrive)
        product = products(settings)[payment.product]  # type: ignore[index]
        current_end = await session.scalar(
            select(Entitlement.ends_at)
            .where(Entitlement.user_id == payment.user_id, Entitlement.ends_at > now)
            .order_by(Entitlement.ends_at.desc())
            .limit(1)
        )
        starts, ends = entitlement_window(product, now, current_end)
        payment.status = "paid"
        payment.provider_payment_id = payment_id
        payment.raw_event_id = event_id
        session.add(
            Entitlement(
                user_id=payment.user_id,
                product=payment.product,
                starts_at=starts,
                ends_at=ends,
                source_payment_id=payment.id,
            )
        )
        return True


async def refund(engine: AsyncEngine, *, payment_id: str, now: datetime) -> bool:
    async with service_session(engine) as session:
        payment = await session.scalar(
            select(Payment).where(Payment.provider_payment_id == payment_id)
        )
        if payment is None or payment.status == "refunded":
            return False
        payment.status = "refunded"
        ent = await session.scalar(
            select(Entitlement).where(Entitlement.source_payment_id == payment.id)
        )
        if ent is not None and ent.ends_at > now:
            old_end = ent.ends_at
            ent.ends_at = max(ent.starts_at, now)
            # Periods bought after this one were chained to its end: move them up.
            shift = old_end - ent.ends_at
            later = await session.scalars(
                select(Entitlement).where(
                    Entitlement.user_id == payment.user_id,
                    Entitlement.id != ent.id,
                    Entitlement.starts_at >= old_end - timedelta(seconds=1),
                )
            )
            for e in later:
                e.starts_at -= shift
                e.ends_at -= shift
        return True


def event_order_and_payment(event: dict[str, Any]) -> tuple[str | None, str | None]:
    payload = event.get("payload") or {}
    pay = ((payload.get("payment") or {}).get("entity")) or {}
    order = ((payload.get("order") or {}).get("entity")) or {}
    return (pay.get("order_id") or order.get("id")), pay.get("id")
