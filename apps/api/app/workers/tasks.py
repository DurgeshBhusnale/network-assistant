"""Worker tasks: nightly ranking, relevance labelling, plus a ping for health checks."""

import logging
import uuid
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.core.db import service_session
from app.domain.models import Goal, Profile
from app.services import billing, ranking
from app.services.loop import active_goal_and_pack
from app.services.relevance import label_contacts

logger = logging.getLogger(__name__)

NIGHTLY_AT = time(2, 0)
WINDOW_MINUTES = 15


async def ping(_ctx: dict[str, Any], value: str) -> str:
    """Round-trip task used by tests and to check a worker is consuming the queue."""
    return value


async def heartbeat(_ctx: dict[str, Any]) -> None:
    """No-op cron: proves the scheduler runs."""
    logger.info("worker_heartbeat")


def due_now(now: datetime, timezone: str) -> bool:
    local = now.astimezone(ZoneInfo(timezone))
    minutes = local.hour * 60 + local.minute - (NIGHTLY_AT.hour * 60 + NIGHTLY_AT.minute)
    return 0 <= minutes < WINDOW_MINUTES


async def rank_due_users(ctx: dict[str, Any]) -> int:
    """Every 15 min, users whose local time just passed 02:00 get the next list (tech spec §7.3).
    Paid: daily. Free: weekly, built early on Monday for the whole week (FR-TODAY-4)."""
    engine = ctx["engine"]
    now = datetime.now(UTC)
    async with service_session(engine) as session:
        rows = (
            await session.execute(
                select(Profile.user_id, Profile.timezone)
                .join(Goal, Goal.user_id == Profile.user_id)
                .where(Goal.status == "active")
            )
        ).all()
    ranked = 0
    for user_id, timezone in rows:
        if not due_now(now, timezone):
            continue
        try:
            async with service_session(engine) as session:
                found = await active_goal_and_pack(session, user_id)
                if found is None:
                    continue
                goal, pack = found
                today = now.astimezone(ZoneInfo(timezone)).date()
                plan = await billing.current_plan(session, user_id, now)
                if plan.kind == "free" and today.weekday() != 0:
                    continue
                for_date = ranking.week_start(today) if plan.kind == "free" else today
                await ranking.rank(session, user_id, goal, pack, today, for_date)
                ranked += 1
        except Exception as exc:
            logger.warning("nightly_rank_failed", extra={"error_type": type(exc).__name__})
    logger.info("nightly_rank_done", extra={"ranked": ranked})
    return ranked


async def label_relevance(ctx: dict[str, Any], user_id: str) -> int:
    router = ctx.get("ai_router")
    if router is None:
        return 0
    return await label_contacts(ctx["engine"], router, uuid.UUID(user_id))
