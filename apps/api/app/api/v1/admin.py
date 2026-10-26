"""Owner-only metrics (FR-AN-2): aggregates only, never contact data (privacy checklist)."""

from datetime import timedelta
from decimal import Decimal

from fastapi import APIRouter
from pydantic import BaseModel
from sqlalchemy import text

from app.api.v1.deps import ClockDep, SettingsDep
from app.core.auth import CurrentUser
from app.core.db import Engine, service_session
from app.core.errors import AppError, ErrorCode

router = APIRouter(prefix="/admin", tags=["admin"])


class FunnelOut(BaseModel):
    signups: int
    accepted_notice: int
    set_goal: int
    imported_contacts: int
    activated: int
    paid: int


class AdminMetrics(BaseModel):
    funnel: FunnelOut
    conversion_pct: float
    activation_pct: float
    warm_replies_7d: int
    active_users_7d: int
    warm_replies_per_active_user: float
    ai_cost_30d_inr: float
    ai_cost_per_active_user_30d_inr: float
    ai_failures_30d: int
    wa_messages_out_30d: int


def _is_admin(user_id: str, admin_ids: str) -> bool:
    return user_id in {x.strip() for x in admin_ids.split(",") if x.strip()}


@router.get("/metrics", response_model=AdminMetrics)
async def metrics(
    user: CurrentUser, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> AdminMetrics:
    if not _is_admin(str(user.id), settings.admin_user_ids):
        raise AppError(ErrorCode.FORBIDDEN, "Admins only.", 403)
    now = clock.now()
    week, month = now - timedelta(days=7), now - timedelta(days=30)
    queries = {
        "signups": "select count(*) from profiles",
        "accepted_notice": "select count(*) from profiles where privacy_notice_version is not null",
        "set_goal": "select count(distinct user_id) from goals",
        "imported_contacts": "select count(distinct user_id) from contacts",
        # Activation (PRD §5.3): 3+ messages sent within 48 h of signup.
        "activated": (
            "select count(*) from (select p.user_id from profiles p join interactions i "
            "on i.user_id = p.user_id and i.type = 'sent' "
            "and i.occurred_at <= p.created_at + interval '48 hours' "
            "group by p.user_id having count(*) >= 3) a"
        ),
        "paid": "select count(distinct user_id) from payments where status = 'paid'",
        "warm_replies": (
            "select count(*) from interactions where type = 'replied' and occurred_at >= :week"
        ),
        "active": "select count(distinct user_id) from interactions where occurred_at >= :week",
        "active_30": "select count(distinct user_id) from interactions where occurred_at >= :month",
        "ai_cost": "select coalesce(sum(cost_inr), 0) from ai_calls where created_at >= :month",
        "ai_failures": "select count(*) from ai_calls where not ok and created_at >= :month",
        "wa_out": (
            "select count(*) from wa_messages where direction = 'out' and created_at >= :month"
        ),
    }
    values: dict[str, int | Decimal] = {}
    async with service_session(engine) as session:
        for name, sql in queries.items():
            values[name] = (
                await session.execute(text(sql), {"week": week, "month": month})
            ).scalar_one()
    signups = int(values["signups"]) or 1
    active = int(values["active"])
    cost = float(values["ai_cost"])
    return AdminMetrics(
        funnel=FunnelOut(
            signups=int(values["signups"]),
            accepted_notice=int(values["accepted_notice"]),
            set_goal=int(values["set_goal"]),
            imported_contacts=int(values["imported_contacts"]),
            activated=int(values["activated"]),
            paid=int(values["paid"]),
        ),
        conversion_pct=round(100 * int(values["paid"]) / signups, 1),
        activation_pct=round(100 * int(values["activated"]) / signups, 1),
        warm_replies_7d=int(values["warm_replies"]),
        active_users_7d=active,
        warm_replies_per_active_user=round(int(values["warm_replies"]) / active, 2)
        if active
        else 0.0,
        ai_cost_30d_inr=round(cost, 2),
        ai_cost_per_active_user_30d_inr=round(cost / int(values["active_30"]), 2)
        if int(values["active_30"])
        else 0.0,
        ai_failures_30d=int(values["ai_failures"]),
        wa_messages_out_30d=int(values["wa_out"]),
    )
