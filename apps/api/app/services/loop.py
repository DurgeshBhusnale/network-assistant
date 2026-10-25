"""The daily loop: Today, sending, interactions, reply check-ins, progress."""

import math
import uuid
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.domain.models import Contact, Draft, Goal, GoalContact, Interaction, Suggestion
from app.domain.models import Pack as PackRow
from app.domain.schemas import (
    CompanyProgress,
    FunnelStep,
    GoalStripOut,
    OutcomeOption,
    PendingReply,
    ProgressOut,
    ReasonOut,
    StageTone,
    StatOut,
    SuggestionContact,
    SuggestionOut,
)
from app.engine.packs import Pack, Stage, parse_pack
from app.engine.relevance import matching_target, target_norms

STATE_ORDER = ["none", "warmed", "asked", "replied", "won"]


def local_day_start(now: datetime, timezone: str) -> datetime:
    local = now.astimezone(ZoneInfo(timezone))
    return datetime.combine(local.date(), time.min, tzinfo=local.tzinfo)


async def active_goal_and_pack(
    session: AsyncSession, user_id: uuid.UUID
) -> tuple[Goal, Pack] | None:
    goal = await session.scalar(
        select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
    )
    if goal is None:
        return None
    row = await session.scalar(select(PackRow).where(PackRow.id == goal.pack_id))
    pack = parse_pack(row.config) if row else None
    if not isinstance(pack, Pack):
        return None
    return goal, pack


def stage_tone(stage: Stage) -> StageTone:
    if stage.role == "thank":
        return "thanks"
    return "ask" if stage.has_ask else "nurture"


def stage_label(pack: Pack, stage_id: str) -> str:
    try:
        return pack.stage(stage_id).label
    except ValueError:
        return stage_id


def _copy(pack: Pack) -> dict[str, Any]:
    return pack.copy_.model_dump()


async def funnel_counts(
    session: AsyncSession, user_id: uuid.UUID, goal: Goal, pack: Pack
) -> dict[str, int]:
    """Distinct contacts per funnel step, from interactions on this goal."""
    roles = {s.id: s.role for s in pack.stages}
    counts: dict[str, set[uuid.UUID]] = {"warmed": set(), "asked": set(), "replied": set()}
    outcome_counts: dict[str, set[uuid.UUID]] = {o: set() for o in pack.outcomes}
    for i in await session.scalars(
        select(Interaction).where(Interaction.user_id == user_id, Interaction.goal_id == goal.id)
    ):
        if i.type == "sent" and roles.get(i.stage or "") == "reconnect":
            counts["warmed"].add(i.contact_id)
        elif i.type == "sent" and roles.get(i.stage or "") == "ask":
            counts["asked"].add(i.contact_id)
        elif i.type == "replied":
            counts["replied"].add(i.contact_id)
        elif i.type == "outcome" and i.outcome in outcome_counts:
            outcome_counts[i.outcome].add(i.contact_id)
    result = {k: len(v) for k, v in counts.items()}
    result.update({k: len(v) for k, v in outcome_counts.items()})
    return result


def goal_strip(goal: Goal, pack: Pack, today: date, counts: dict[str, int]) -> GoalStripOut:
    copy = _copy(pack)
    state_labels: dict[str, str] = copy.get("state_labels", {})
    success = pack.success_metric
    target = goal.params.get(success.target_param)
    total = (goal.ends_on - goal.starts_on).days if goal.ends_on else pack.duration_days
    stats = [
        StatOut(label=state_labels.get(k, k), value=str(counts.get(k, 0)))
        for k in ("warmed", "asked", "replied")
    ]
    stats.append(
        StatOut(
            label=copy.get("success_label", success.outcome),
            value=f"{counts.get(success.outcome, 0)} / {target}"
            if target
            else str(counts.get(success.outcome, 0)),
            highlight=True,
        )
    )
    title = str(goal.params.get("role") or copy.get("goal_strip_label") or pack.name)
    return GoalStripOut(
        goal_id=goal.id,
        label=copy.get("goal_strip_label", pack.name),
        title=title,
        day_number=max(1, (today - goal.starts_on).days + 1),
        total_days=total,
        days_left=max(0, (goal.ends_on - today).days) if goal.ends_on else None,
        stats=stats,
    )


async def suggestions_for(
    session: AsyncSession, user_id: uuid.UUID, pack: Pack | None, for_date: date
) -> list[SuggestionOut]:
    rows = (
        await session.execute(
            select(Suggestion, Contact)
            .join(Contact, Contact.id == Suggestion.contact_id)
            .where(
                Suggestion.user_id == user_id,
                Suggestion.for_date == for_date,
                Suggestion.status.in_(["pending", "opened", "sent"]),
                Contact.deleted_at.is_(None),
            )
            .order_by(Suggestion.score.desc(), Suggestion.created_at)
        )
    ).all()
    drafts = {
        d.suggestion_id: d.id
        for d in await session.scalars(
            select(Draft).where(
                Draft.user_id == user_id,
                Draft.suggestion_id.in_([s.id for s, _ in rows] or [uuid.uuid4()]),
            )
        )
    }
    out = []
    for s, c in rows:
        stage = pack.stage(s.stage) if pack else None
        out.append(
            SuggestionOut(
                id=s.id,
                contact=SuggestionContact(
                    id=c.id,
                    full_name=c.full_name,
                    title=c.title,
                    company=c.company,
                    how_known=c.how_known,
                ),
                stage=s.stage,
                stage_label=stage.label if stage else s.stage,
                stage_tone=stage_tone(stage) if stage else "nurture",
                reasons=[
                    ReasonOut(text=r["text"], highlight=bool(r.get("highlight")))
                    for r in s.reasons
                    if "text" in r
                ],
                status=s.status,
                draft_id=drafts.get(s.id),
            )
        )
    return out


def minutes_for(pack: Pack | None, open_items: int) -> int:
    per = float(_copy(pack).get("minutes_per_person", 1.5)) if pack else 1.5
    return math.ceil(open_items * per)


async def sends_today(session: AsyncSession, user_id: uuid.UUID, day_start: datetime) -> int:
    count = await session.scalar(
        select(func.count(Draft.id)).where(
            Draft.user_id == user_id, Draft.send_opened_at >= day_start
        )
    )
    return int(count or 0)


def _advance(gc: GoalContact, state: str) -> None:
    if STATE_ORDER.index(state) > STATE_ORDER.index(gc.state):
        gc.state = state


async def goal_contact(
    session: AsyncSession, user_id: uuid.UUID, goal: Goal, contact_id: uuid.UUID
) -> GoalContact:
    gc = await session.scalar(
        select(GoalContact).where(
            GoalContact.goal_id == goal.id,
            GoalContact.contact_id == contact_id,
            GoalContact.user_id == user_id,
        )
    )
    if gc is None:
        gc = GoalContact(goal_id=goal.id, contact_id=contact_id, user_id=user_id, state="none")
        session.add(gc)
        await session.flush()
    return gc


def apply_sent(gc: GoalContact, stage: Stage, now: datetime) -> None:
    gc.last_sent_at = now
    if stage.role == "reconnect":
        _advance(gc, "warmed")
    elif stage.role in ("ask", "follow_up"):
        _advance(gc, "asked")
    elif stage.role == "thank":
        gc.thanked_at = now


def apply_replied(gc: GoalContact) -> None:
    if gc.state == "asked":
        gc.state = "replied"


def apply_outcome(gc: GoalContact, outcome: str) -> None:
    gc.state = "won"
    gc.outcome = outcome


def require_outcome(pack: Pack, outcome: str | None) -> str:
    if outcome is None or outcome not in pack.outcomes:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: outcome", 422)
    return outcome


async def pending_replies(
    session: AsyncSession, user_id: uuid.UUID, pack: Pack | None, today: date, timezone: str
) -> list[PendingReply]:
    window = pack.reply_check_in if pack else {"from_days": 2, "to_days": 5}
    tz = ZoneInfo(timezone)
    latest: dict[uuid.UUID, Interaction] = {}
    for i in await session.scalars(
        select(Interaction)
        .where(
            Interaction.user_id == user_id,
            Interaction.type.in_(["sent", "replied", "no_reply", "outcome"]),
        )
        .order_by(Interaction.occurred_at)
    ):
        latest[i.contact_id] = i
    due = []
    for contact_id, i in latest.items():
        if i.type != "sent":
            continue
        days = (today - i.occurred_at.astimezone(tz).date()).days
        if window["from_days"] <= days <= window["to_days"]:
            due.append((contact_id, i, days))
    if not due:
        return []
    contacts = {
        c.id: c
        for c in await session.scalars(
            select(Contact).where(
                Contact.user_id == user_id,
                Contact.id.in_([d[0] for d in due]),
                Contact.deleted_at.is_(None),
            )
        )
    }
    out = []
    for contact_id, i, days in sorted(due, key=lambda d: d[1].occurred_at):
        c = contacts.get(contact_id)
        if c is None:
            continue
        stage = None
        if pack and i.stage:
            try:
                stage = pack.stage(i.stage)
            except ValueError:
                stage = None
        out.append(
            PendingReply(
                contact=SuggestionContact(
                    id=c.id,
                    full_name=c.full_name,
                    title=c.title,
                    company=c.company,
                    how_known=c.how_known,
                ),
                sent_at=i.occurred_at,
                days_ago=days,
                stage=i.stage,
                stage_label=_copy(pack)
                .get("stage_past", {})
                .get(i.stage, stage.label if stage else None)
                if pack
                else None,
                stage_has_ask=bool(stage and stage.has_ask),
            )
        )
    return out


def outcome_options(pack: Pack | None) -> list[OutcomeOption]:
    if pack is None:
        return []
    labels: dict[str, str] = _copy(pack).get("outcome_labels", {})
    return [OutcomeOption(id=o, label=labels.get(o, o)) for o in pack.outcomes]


async def progress(
    session: AsyncSession, user_id: uuid.UUID, goal: Goal, pack: Pack, today: date, timezone: str
) -> ProgressOut:
    counts = await funnel_counts(session, user_id, goal, pack)
    copy = _copy(pack)
    state_labels: dict[str, str] = copy.get("state_labels", {})
    outcome_past: dict[str, str] = copy.get("outcome_past", {})
    funnel_labels: dict[str, str] = copy.get("funnel_labels", {})
    funnel = [
        FunnelStep(
            key=k,
            label=funnel_labels.get(k, k),
            count=counts.get(k, 0),
            highlight=k == pack.success_metric.outcome,
        )
        for k in ("warmed", "asked", "replied", *pack.outcomes)
    ]

    tz = ZoneInfo(timezone)
    week_start = today - timedelta(days=today.weekday())
    since = datetime.combine(week_start, time.min, tzinfo=tz)
    warm = await session.scalar(
        select(func.count(Interaction.id)).where(
            Interaction.user_id == user_id,
            Interaction.type == "replied",
            Interaction.occurred_at >= since,
        )
    )

    targets = target_norms(pack, goal.params)
    display = {t: name for t, name in zip(targets, goal.params.get("companies", []), strict=False)}
    people: dict[str, list[GoalContact]] = {t: [] for t in targets}
    rows = (
        await session.execute(
            select(GoalContact, Contact.company_norm)
            .join(Contact, Contact.id == GoalContact.contact_id)
            .where(
                GoalContact.goal_id == goal.id,
                GoalContact.user_id == user_id,
                Contact.deleted_at.is_(None),
            )
        )
    ).all()
    for gc, company_norm in rows:
        match = matching_target(company_norm, targets)
        if match:
            people[match].append(gc)
    by_company = []
    for t in targets:
        group = people[t]
        best = max(group, key=lambda g: STATE_ORDER.index(g.state), default=None)
        if best is None:
            status = "No one yet"
        elif best.state == "won":
            status = outcome_past.get(best.outcome or "", best.outcome or "Done")
        elif best.state == "none":
            status = "Not contacted yet"
        else:
            status = state_labels.get(best.state, best.state)
        n = len(group)
        prefix = f"{n} {'person' if n == 1 else 'people'} · " if n else ""
        by_company.append(
            CompanyProgress(company=display.get(t, t), people=n, status=prefix + status)
        )

    target = goal.params.get(pack.success_metric.target_param)
    title_tpl = copy.get("progress_title")
    headline = (
        title_tpl.format(count=counts.get(pack.success_metric.outcome, 0), target=target)
        if title_tpl and target
        else None
    )
    return ProgressOut(
        goal=goal_strip(goal, pack, today, counts),
        headline=headline,
        warm_replies_this_week=int(warm or 0),
        funnel=funnel,
        by_company=by_company,
    )
