"""Today, suggestions, sending, interactions, reply check-ins, progress (Sprint 4)."""

import uuid
from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.deps import AIRouterDep
from app.analytics.track import track, track_many
from app.api.v1.deps import ClockDep, SettingsDep
from app.api.v1.drafts import create_draft_for
from app.core.auth import CurrentUser
from app.core.clock import local_today
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.core.ratelimit import limit
from app.domain.models import Contact, Draft, Interaction, Suggestion
from app.domain.schemas import (
    DraftOut,
    InteractionIn,
    InteractionOut,
    ProgressOut,
    RepliesOut,
    SendIn,
    SendOut,
    SnoozeIn,
    SuggestionDraftIn,
    TodayOut,
)
from app.engine.send import edit_ratio, whatsapp_url
from app.services import billing, loop, ranking
from app.services.contacts import get_contact
from app.services.profiles import ensure_profile

router = APIRouter(tags=["daily loop"])


def _not_found(what: str) -> AppError:
    return AppError(ErrorCode.NOT_FOUND, f"{what} not found.", 404)


@router.get("/today", response_model=TodayOut)
async def get_today(user: CurrentUser, engine: Engine, clock: ClockDep) -> TodayOut:
    now = clock.now()
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        today = local_today(clock, profile.timezone)
        plan = await billing.current_plan(session, user.id, now)
        weekly = plan.kind == "free"
        for_date = ranking.week_start(today) if weekly else today
        found = await loop.active_goal_and_pack(session, user.id)
        contacts_count = int(
            await session.scalar(
                select(func.count(Contact.id)).where(
                    Contact.user_id == user.id, Contact.deleted_at.is_(None)
                )
            )
            or 0
        )
        goal_strip = None
        pack = None
        first_view = False
        if found is not None:
            goal, pack = found
            if contacts_count and not await ranking.has_list(session, user.id, for_date):
                await ranking.rank(session, user.id, goal, pack, today, for_date)  # FR-ONB-2
                first_view = True
            counts = await loop.funnel_counts(session, user.id, goal, pack)
            goal_strip = loop.goal_strip(goal, pack, today, counts)
        items = await loop.suggestions_for(session, user.id, pack, for_date)
        open_items = [i for i in items if i.status in ("pending", "opened")]
        result = TodayOut(
            date=today,
            weekly=weekly,
            display_name=profile.display_name,
            goal=goal_strip,
            items=items,
            minutes=loop.minutes_for(pack, len(open_items)),
            contacts_count=contacts_count,
            done=bool(items) and not open_items,
        )
    if first_view:
        await track_many(engine, user.id, [("suggestion_shown", {"stage": i.stage}) for i in items])
    return result


async def _suggestion(
    session: AsyncSession, user_id: uuid.UUID, suggestion_id: uuid.UUID
) -> Suggestion:
    s: Suggestion | None = await session.scalar(
        select(Suggestion).where(Suggestion.id == suggestion_id, Suggestion.user_id == user_id)
    )
    if s is None:
        raise _not_found("Suggestion")
    return s


@router.post("/suggestions/{suggestion_id}/snooze", status_code=204)
async def snooze(
    suggestion_id: uuid.UUID, body: SnoozeIn, user: CurrentUser, engine: Engine, clock: ClockDep
) -> None:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        s = await _suggestion(session, user.id, suggestion_id)
        s.status = "snoozed"
        s.snoozed_until = local_today(clock, profile.timezone) + timedelta(days=body.days)


@router.post("/suggestions/{suggestion_id}/dismiss", status_code=204)
async def dismiss(
    suggestion_id: uuid.UUID, user: CurrentUser, engine: Engine, clock: ClockDep
) -> None:
    async with user_session(engine, user) as session:
        s = await _suggestion(session, user.id, suggestion_id)
        s.status = "dismissed"
        found = await loop.active_goal_and_pack(session, user.id)
        if found is not None:
            gc = await loop.goal_contact(session, user.id, found[0], s.contact_id)
            gc.dismissed_at = clock.now()


@router.post(
    "/suggestions/{suggestion_id}/draft",
    response_model=DraftOut,
    status_code=201,
    dependencies=[Depends(limit("drafts", 20, 60))],
)
async def draft_for_suggestion(
    suggestion_id: uuid.UUID,
    body: SuggestionDraftIn,
    user: CurrentUser,
    engine: Engine,
    ai: AIRouterDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> DraftOut:
    async with user_session(engine, user) as session:
        s = await _suggestion(session, user.id, suggestion_id)
        existing = await session.scalar(
            select(Draft.id).where(Draft.suggestion_id == s.id, Draft.user_id == user.id)
        )
        contact_id, stage = s.contact_id, s.stage
        reasons = [r["text"] for r in s.reasons if isinstance(r, dict) and "text" in r]
        if s.status == "pending":
            s.status = "opened"
    if existing is not None:
        raise AppError(ErrorCode.CONFLICT, "A draft already exists for this suggestion.", 409)
    result = await create_draft_for(
        engine,
        user,
        ai,
        settings,
        clock,
        contact_id,
        stage,
        body.tone,
        suggestion_id=suggestion_id,
        reasons=reasons,
    )
    await track(engine, user.id, "suggestion_opened", {"stage": stage})
    return result


@router.post(
    "/drafts/{draft_id}/send",
    response_model=SendOut,
    dependencies=[Depends(limit("send", 30, 60))],
)
async def send_draft(
    draft_id: uuid.UUID,
    body: SendIn,
    user: CurrentUser,
    engine: Engine,
    settings: SettingsDep,
    clock: ClockDep,
) -> SendOut:
    """Builds the link that opens the user's own app (ADR-0004). Counts toward the daily cap once
    per draft (FR-SEND-5). Nothing is recorded as sent until the user confirms."""
    now = clock.now()
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        draft = await session.scalar(
            select(Draft).where(Draft.id == draft_id, Draft.user_id == user.id)
        )
        if draft is None:
            raise _not_found("Draft")
        contact = await get_contact(session, user.id, draft.contact_id)
        day_start = loop.local_day_start(now, profile.timezone)
        used = await loop.sends_today(session, user.id, day_start)
        counted = draft.send_opened_at is not None and draft.send_opened_at >= day_start
        if not counted and used >= settings.daily_send_cap:
            raise AppError(
                ErrorCode.SEND_CAP_REACHED,
                f"You've opened {settings.daily_send_cap} messages today. That's the daily limit, "
                "so every message stays personal. Try again tomorrow.",
                429,
            )
        text = (draft.final_text or draft.text).strip()
        if body.channel == "whatsapp":
            if not contact.phones:
                raise AppError(ErrorCode.NO_PHONE, "No phone number for this person.", 422)
            open_url: str | None = whatsapp_url(contact.phones[0], text)
        else:
            open_url = contact.linkedin_url
        if not counted:
            draft.send_opened_at = now
            used += 1
        draft.sent_channel = body.channel
        return SendOut(
            open_url=open_url,
            copy_text=text,
            sends_left_today=max(0, settings.daily_send_cap - used),
        )


@router.post("/interactions", response_model=InteractionOut, status_code=201)
async def log_interaction(
    body: InteractionIn, user: CurrentUser, engine: Engine, clock: ClockDep
) -> InteractionOut:
    now = clock.now()
    events: list[tuple[str, dict[str, Any]]] = []
    thank = False
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        contact = await get_contact(session, user.id, body.contact_id)
        found = await loop.active_goal_and_pack(session, user.id)
        goal, pack = found if found else (None, None)
        gc = await loop.goal_contact(session, user.id, goal, contact.id) if goal else None
        stage_id = None
        outcome = None

        if body.type == "sent":
            if body.draft_id is None:
                raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: draft_id", 422)
            draft = await session.scalar(
                select(Draft).where(Draft.id == body.draft_id, Draft.user_id == user.id)
            )
            if draft is None or draft.contact_id != contact.id:
                raise _not_found("Draft")
            if draft.sent_at is not None:
                raise AppError(ErrorCode.CONFLICT, "Already marked as sent.", 409)
            draft.sent_at = now
            draft.sent_channel = body.channel or draft.sent_channel or "other"
            stage_id = draft.stage
            if draft.suggestion_id is not None:
                s = await session.get(Suggestion, draft.suggestion_id)
                if s is not None and s.user_id == user.id:
                    s.status = "sent"
            if gc is not None and pack is not None:
                loop.apply_sent(gc, pack.stage(draft.stage), now)
            events.append(
                (
                    "draft_sent",
                    {
                        "channel": draft.sent_channel,
                        "edit_ratio": edit_ratio(draft.text, draft.final_text),
                    },
                )
            )
        elif body.type == "replied":
            if gc is not None:
                loop.apply_replied(gc)
            last_sent = await session.scalar(
                select(Interaction)
                .where(
                    Interaction.user_id == user.id,
                    Interaction.contact_id == contact.id,
                    Interaction.type == "sent",
                )
                .order_by(Interaction.occurred_at.desc())
                .limit(1)
            )
            events.append(
                (
                    "reply_logged",
                    {
                        "days_to_reply": (now - last_sent.occurred_at).days if last_sent else None,
                        "stage": last_sent.stage if last_sent else None,
                    },
                )
            )
        elif body.type == "outcome":
            if pack is None or goal is None or gc is None:
                raise AppError(ErrorCode.NO_ACTIVE_GOAL, "Set a goal first.", 409)
            outcome = loop.require_outcome(pack, body.outcome)
            loop.apply_outcome(gc, outcome)
            today = local_today(clock, profile.timezone)
            plan = await billing.current_plan(session, user.id, now)
            list_date = ranking.week_start(today) if plan.kind == "free" else today
            await ranking.add_thank_suggestion(session, user.id, goal, pack, contact.id, list_date)
            thank = True
            events.append(("outcome_logged", {"type": outcome}))

        interaction = Interaction(
            user_id=user.id,
            contact_id=contact.id,
            goal_id=goal.id if goal else None,
            type=body.type,
            stage=stage_id,
            outcome=outcome,
            channel=body.channel,
            occurred_at=now,
        )
        session.add(interaction)
        contact.last_interaction_at = now
        await session.flush()
        result = InteractionOut(
            id=interaction.id,
            type=interaction.type,
            stage=stage_id,
            outcome=outcome,
            occurred_at=now,
            thank_suggestion=thank,
        )
    await track_many(engine, user.id, events)
    return result


@router.get("/replies/pending", response_model=RepliesOut)
async def replies_pending(user: CurrentUser, engine: Engine, clock: ClockDep) -> RepliesOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        found = await loop.active_goal_and_pack(session, user.id)
        pack = found[1] if found else None
        today = local_today(clock, profile.timezone)
        items = await loop.pending_replies(session, user.id, pack, today, profile.timezone)
        return RepliesOut(items=items, outcomes=loop.outcome_options(pack))


@router.get("/progress", response_model=ProgressOut)
async def get_progress(user: CurrentUser, engine: Engine, clock: ClockDep) -> ProgressOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        found = await loop.active_goal_and_pack(session, user.id)
        if found is None:
            return ProgressOut(
                goal=None, headline=None, warm_replies_this_week=0, funnel=[], by_company=[]
            )
        goal, pack = found
        return await loop.progress(
            session, user.id, goal, pack, local_today(clock, profile.timezone), profile.timezone
        )
