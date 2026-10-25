"""Drafts (FR-DRAFT-*) and the style profile (FR-ONB-1 step 3)."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.ai.deps import AIRouterDep
from app.ai.prompts import render
from app.ai.router import AIRouter, AIUnavailableError, StyleOutput
from app.analytics.track import track
from app.api.v1.deps import ClockDep, SettingsDep
from app.billing.limits import Decision, can_create_draft, can_regenerate, regenerations_left
from app.core.auth import AuthUser, CurrentUser
from app.core.clock import Clock
from app.core.config import Settings
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.core.ratelimit import limit
from app.domain.models import Draft, StyleProfile
from app.domain.schemas import (
    DraftCreate,
    DraftEdit,
    DraftOut,
    DraftRegenerate,
    StyleOut,
    StyleSamplesUpdate,
    Tone,
)
from app.services import billing
from app.services import contacts as contacts_svc
from app.services.drafts import count_paid_draft, draft_out, generate, load_context
from app.services.profiles import ensure_profile

router = APIRouter(tags=["drafts"])

_LIMIT_MESSAGES = {
    "FREE_LIMIT_REACHED": "You've used your free drafts this month.",
    "FREE_REGEN_LIMIT_REACHED": "You've used the free rewrites for this draft.",
    "FAIR_USE_REACHED": "You've reached the fair-use limit for this Sprint.",
}


def _deny(decision: Decision) -> None:
    if not decision.allowed and decision.code is not None:
        raise AppError(ErrorCode(decision.code.value), _LIMIT_MESSAGES[decision.code.value], 402)


def _ai_down(_exc: AIUnavailableError) -> AppError:
    return AppError(ErrorCode.AI_UNAVAILABLE, "Couldn't write a draft right now. Try again.", 503)


@router.get("/style", response_model=StyleOut)
async def get_style(user: CurrentUser, engine: Engine) -> StyleOut:
    async with user_session(engine, user) as session:
        style = await session.scalar(select(StyleProfile).where(StyleProfile.user_id == user.id))
        return StyleOut(
            samples=list(style.samples) if style else [], summary=style.summary if style else None
        )


@router.put("/style/samples", response_model=StyleOut)
async def put_style_samples(
    body: StyleSamplesUpdate, user: CurrentUser, engine: Engine, ai: AIRouterDep, clock: ClockDep
) -> StyleOut:
    summary: str | None = None
    if body.samples:
        prompt = render("style_summary.v1", samples="\n---\n".join(body.samples))
        try:
            out, _ = await ai.complete_json(
                "summarise_style", "style_summary.v1", prompt, StyleOutput, user_id=user.id
            )
        except AIUnavailableError as exc:
            raise _ai_down(exc) from exc
        summary = out.summary.strip()[:800]
    async with user_session(engine, user) as session:
        style = await session.scalar(select(StyleProfile).where(StyleProfile.user_id == user.id))
        if style is None:
            style = StyleProfile(user_id=user.id)
            session.add(style)
        style.samples = body.samples
        style.summary = summary
        style.updated_at = clock.now()
        await session.flush()
        return StyleOut(samples=body.samples, summary=summary)


@router.post(
    "/contacts/{contact_id}/draft",
    response_model=DraftOut,
    status_code=201,
    dependencies=[Depends(limit("drafts", 20, 60))],
)
async def create_draft(
    contact_id: uuid.UUID,
    body: DraftCreate,
    user: CurrentUser,
    engine: Engine,
    ai: AIRouterDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> DraftOut:
    return await create_draft_for(
        engine, user, ai, settings, clock, contact_id, body.stage, body.tone
    )


async def create_draft_for(
    engine: AsyncEngine,
    user: AuthUser,
    ai: AIRouter,
    settings: Settings,
    clock: Clock,
    contact_id: uuid.UUID,
    stage: str,
    tone: Tone | None,
    *,
    suggestion_id: uuid.UUID | None = None,
    reasons: list[str] | None = None,
) -> DraftOut:
    """Shared by the Person page and Today suggestions (FR-DRAFT-1)."""
    now = clock.now()
    limits = billing.limits_from(settings)
    # Read phase: limits and context in a short transaction (no AI call while holding it).
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        contact = await contacts_svc.get_contact(session, user.id, contact_id)
        ctx = await load_context(session, user.id, contact, stage)
        plan = await billing.current_plan(session, user.id, now)
        used = await billing.drafts_this_month(session, user.id, now, profile.timezone)
        decision = can_create_draft(plan, used, limits)
        _deny(decision)
        entitlement = await billing.active_entitlement(session, user.id, now)

    try:
        gen = await generate(ai, ctx, tone, user.id, variation=False)
    except AIUnavailableError as exc:
        raise _ai_down(exc) from exc

    async with user_session(engine, user) as session:
        draft = Draft(
            user_id=user.id,
            suggestion_id=suggestion_id,
            contact_id=contact_id,
            stage=ctx.stage.id,
            tone=tone,
            language="hinglish" if tone == "hinglish" else ctx.profile.language,
            provider=gen.provider,
            model=gen.model,
            prompt_version=gen.prompt_version,
            text=gen.text,
            factcheck={"unsupported": gen.unsupported, "warnings": gen.warnings},
        )
        session.add(draft)
        await session.flush()
        await session.refresh(draft)
        result = draft_out(
            draft,
            ctx.pack,
            regenerations_left=regenerations_left(plan, 0, limits),
            drafts_left_this_month=decision.remaining,
            reasons=reasons,
        )
    if entitlement is not None:
        await count_paid_draft(engine, entitlement.id)
    await track(
        engine,
        user.id,
        "draft_generated",
        {
            "model": gen.model,
            "prompt_version": gen.prompt_version,
            "latency_ms": gen.latency_ms,
            "tier": plan.kind,
        },
    )
    return result


async def _load_draft(session: AsyncSession, user_id: uuid.UUID, draft_id: uuid.UUID) -> Draft:
    draft: Draft | None = await session.scalar(
        select(Draft).where(Draft.id == draft_id, Draft.user_id == user_id)
    )
    if draft is None:
        raise AppError(ErrorCode.NOT_FOUND, "Draft not found.", 404)
    return draft


@router.get("/drafts/{draft_id}", response_model=DraftOut)
async def get_draft(
    draft_id: uuid.UUID, user: CurrentUser, engine: Engine, settings: SettingsDep, clock: ClockDep
) -> DraftOut:
    async with user_session(engine, user) as session:
        draft = await _load_draft(session, user.id, draft_id)
        contact = await contacts_svc.get_contact(session, user.id, draft.contact_id)
        ctx = await load_context(session, user.id, contact, draft.stage)
        plan = await billing.current_plan(session, user.id, clock.now())
        return draft_out(
            draft,
            ctx.pack,
            regenerations_left=regenerations_left(
                plan, draft.regenerations, billing.limits_from(settings)
            ),
            drafts_left_this_month=None,
        )


@router.post(
    "/drafts/{draft_id}/regenerate",
    response_model=DraftOut,
    dependencies=[Depends(limit("drafts", 20, 60))],
)
async def regenerate_draft(
    draft_id: uuid.UUID,
    body: DraftRegenerate,
    user: CurrentUser,
    engine: Engine,
    ai: AIRouterDep,
    settings: SettingsDep,
    clock: ClockDep,
) -> DraftOut:
    limits = billing.limits_from(settings)
    async with user_session(engine, user) as session:
        draft = await _load_draft(session, user.id, draft_id)
        if draft.sent_at is not None:
            raise AppError(ErrorCode.CONFLICT, "This message was already sent.", 409)
        plan = await billing.current_plan(session, user.id, clock.now())
        _deny(can_regenerate(plan, draft.regenerations, limits))
        contact = await contacts_svc.get_contact(session, user.id, draft.contact_id)
        ctx = await load_context(session, user.id, contact, draft.stage)

    try:
        gen = await generate(ai, ctx, body.tone, user.id, variation=body.tone is None)
    except AIUnavailableError as exc:
        raise _ai_down(exc) from exc

    async with user_session(engine, user) as session:
        draft = await _load_draft(session, user.id, draft_id)
        draft.text = gen.text
        draft.final_text = None
        draft.tone = body.tone
        if body.tone == "hinglish":
            draft.language = "hinglish"
        draft.model = gen.model
        draft.provider = gen.provider
        draft.factcheck = {"unsupported": gen.unsupported, "warnings": gen.warnings}
        draft.regenerations += 1
        await session.flush()
        result = draft_out(
            draft,
            ctx.pack,
            regenerations_left=regenerations_left(plan, draft.regenerations, limits),
            drafts_left_this_month=None,
        )
    await track(engine, user.id, "draft_regenerated", {"tone": body.tone or "another_version"})
    return result


@router.patch("/drafts/{draft_id}", response_model=DraftOut)
async def edit_draft(
    draft_id: uuid.UUID,
    body: DraftEdit,
    user: CurrentUser,
    engine: Engine,
    settings: SettingsDep,
    clock: ClockDep,
) -> DraftOut:
    async with user_session(engine, user) as session:
        draft = await _load_draft(session, user.id, draft_id)
        if draft.sent_at is not None:
            raise AppError(ErrorCode.CONFLICT, "This message was already sent.", 409)
        draft.final_text = body.final_text.strip()
        await session.flush()
        contact = await contacts_svc.get_contact(session, user.id, draft.contact_id)
        ctx = await load_context(session, user.id, contact, draft.stage)
        plan = await billing.current_plan(session, user.id, clock.now())
        return draft_out(
            draft,
            ctx.pack,
            regenerations_left=regenerations_left(
                plan, draft.regenerations, billing.limits_from(settings)
            ),
            drafts_left_this_month=None,
        )
