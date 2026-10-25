"""Worker tasks: nightly ranking, relevance labelling, plus a ping for health checks."""

import logging
import uuid
from datetime import UTC, datetime, time
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select

from app.channels.whatsapp.handler import handle_inbound, send_daily_briefs
from app.channels.whatsapp.inbound import Inbound, SharedContact
from app.core.db import service_session
from app.core.storage import Storage
from app.domain.models import Goal, Profile
from app.services import billing, ranking
from app.services.captures import process_capture as process_capture_svc
from app.services.captures import sweep_audio, sweep_transcripts
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


async def process_capture(ctx: dict[str, Any], capture_id: str) -> None:
    router = ctx.get("ai_router")
    if router is None:
        return
    await process_capture_svc(
        ctx["engine"], router, Storage(ctx["settings"]), uuid.UUID(capture_id)
    )


async def sweep_captures(ctx: dict[str, Any]) -> None:
    """Hourly: leftover audio (> 1 h) and unconfirmed capture text (> 24 h)."""
    now = datetime.now(UTC)
    audio = await sweep_audio(ctx["engine"], Storage(ctx["settings"]), now)
    texts = await sweep_transcripts(ctx["engine"], now)
    logger.info("capture_sweep_done", extra={"audio_deleted": audio, "texts_cleared": texts})


async def handle_whatsapp(ctx: dict[str, Any], message: dict[str, Any]) -> None:
    contacts = [SharedContact(**c) for c in message.get("contacts", [])]
    inbound = Inbound(**{**message, "contacts": contacts})
    await handle_inbound(ctx["engine"], ctx.get("ai_router"), ctx["wa"], ctx["settings"], inbound)


async def send_briefs(ctx: dict[str, Any]) -> None:
    sent = await send_daily_briefs(ctx["engine"], ctx["wa"], ctx["settings"])
    logger.info("wa_briefs_done", extra={"sent": sent})
