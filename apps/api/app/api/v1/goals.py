"""Goals (FR-GOAL-2/3/4): create, read the active goal, update params/status."""

import uuid
from datetime import date

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.track import track
from app.api.v1.deps import ClockDep, SettingsDep
from app.core.auth import CurrentUser
from app.core.clock import local_today
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.domain.models import Goal
from app.domain.models import Pack as PackRow
from app.domain.schemas import GoalCreate, GoalOut, GoalUpdate
from app.engine.goals import GoalParamsError, goal_end_date, validate_goal_params
from app.engine.packs import Pack, parse_pack
from app.services.profiles import ensure_profile
from app.workers.queue import enqueue

router = APIRouter(tags=["goals"])


def goal_out(goal: Goal, today: date) -> GoalOut:
    return GoalOut(
        id=goal.id,
        pack_id=goal.pack_id,
        params=goal.params,
        status=goal.status,
        starts_on=goal.starts_on,
        ends_on=goal.ends_on,
        day_number=max(1, (today - goal.starts_on).days + 1),
        days_left=max(0, (goal.ends_on - today).days) if goal.ends_on else None,
    )


async def _active_pack(session: AsyncSession, pack_id: str) -> Pack:
    row = await session.scalar(select(PackRow).where(PackRow.id == pack_id))
    pack = parse_pack(row.config) if row is not None else None
    if row is None or row.status != "active" or not isinstance(pack, Pack):
        raise AppError(ErrorCode.PACK_NOT_AVAILABLE, "That goal isn't available yet.", 422)
    return pack


def _validated(pack: Pack, params: dict[str, object]) -> dict[str, object]:
    try:
        return validate_goal_params(pack, params)
    except GoalParamsError as exc:
        raise AppError(
            ErrorCode.VALIDATION_ERROR, "Check these fields: " + ", ".join(exc.fields), 422
        ) from exc


def _already_active() -> AppError:
    return AppError(
        ErrorCode.GOAL_ALREADY_ACTIVE,
        "You already have an active goal. Pause or end it first.",
        409,
    )


@router.post("/goals", response_model=GoalOut, status_code=201)
async def create_goal(
    body: GoalCreate,
    request: Request,
    user: CurrentUser,
    engine: Engine,
    settings: SettingsDep,
    clock: ClockDep,
) -> GoalOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        if profile.privacy_notice_version != settings.privacy_notice_version:
            raise AppError(
                ErrorCode.PRIVACY_NOTICE_REQUIRED, "Accept the privacy notice first.", 403
            )
        pack = await _active_pack(session, body.pack_id)
        params = _validated(pack, body.params)
        today = local_today(clock, profile.timezone)
        goal = Goal(
            user_id=user.id,
            pack_id=pack.id,
            params=params,
            starts_on=today,
            ends_on=goal_end_date(pack, today),
        )
        session.add(goal)
        try:
            await session.flush()
        except IntegrityError as exc:
            raise _already_active() from exc
        if profile.onboarding_step == "goal":
            profile.onboarding_step = "import"
        await session.refresh(goal)
        result = goal_out(goal, today)
    await track(engine, user.id, "goal_created", {"pack_id": pack.id})
    await enqueue(request, "label_relevance", str(user.id))
    return result


@router.get("/goals/active", response_model=GoalOut | None)
async def get_active_goal(user: CurrentUser, engine: Engine, clock: ClockDep) -> GoalOut | None:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        goal = await session.scalar(
            select(Goal).where(Goal.user_id == user.id, Goal.status == "active")
        )
        return goal_out(goal, local_today(clock, profile.timezone)) if goal else None


@router.get("/goals/current", response_model=GoalOut | None)
async def get_current_goal(user: CurrentUser, engine: Engine, clock: ClockDep) -> GoalOut | None:
    """The goal Settings manages: the active one, else the latest paused one (so it can resume)."""
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        goal = await session.scalar(
            select(Goal)
            .where(Goal.user_id == user.id, Goal.status.in_(("active", "paused")))
            .order_by((Goal.status == "active").desc(), Goal.created_at.desc())
            .limit(1)
        )
        return goal_out(goal, local_today(clock, profile.timezone)) if goal else None


@router.patch("/goals/{goal_id}", response_model=GoalOut)
async def update_goal(
    goal_id: uuid.UUID, body: GoalUpdate, user: CurrentUser, engine: Engine, clock: ClockDep
) -> GoalOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        goal = await session.scalar(select(Goal).where(Goal.id == goal_id, Goal.user_id == user.id))
        if goal is None:
            raise AppError(ErrorCode.NOT_FOUND, "Goal not found.", 404)
        if body.params is not None:
            pack = await _active_pack(session, goal.pack_id)
            goal.params = _validated(pack, body.params)
        if body.status is not None:
            goal.status = body.status
        try:
            await session.flush()
        except IntegrityError as exc:
            raise _already_active() from exc
        return goal_out(goal, local_today(clock, profile.timezone))
