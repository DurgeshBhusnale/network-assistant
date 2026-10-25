"""Ranking I/O (FR-TODAY-1, FR-ONB-2): gather signals, score with app/engine, write suggestions.

Works in a user (RLS) session for on-demand runs and in a service session for the nightly worker;
every query filters by user_id explicitly either way.
"""

import uuid
from collections import defaultdict
from datetime import date, timedelta
from typing import Any

from sqlalchemy import and_, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import (
    CalendarEvent,
    Contact,
    Goal,
    GoalContact,
    Interaction,
    Suggestion,
    Trigger,
)
from app.engine.packs import Pack
from app.engine.ranking import Scored, Signals, score
from app.engine.ranking import select as select_daily
from app.engine.relevance import deterministic_label, matching_target, target_norms, weight

FORCED_KIND = "follow_up_date"  # suggestions created from capture follow-up dates (Sprint 5)


def week_start(day: date) -> date:
    return day - timedelta(days=day.weekday())


def is_forced(suggestion: Suggestion) -> bool:
    return any(isinstance(r, dict) and r.get("kind") == FORCED_KIND for r in suggestion.reasons)


def _birthday_today(birthday: date | None, today: date) -> bool:
    if birthday is None:
        return False
    if (birthday.month, birthday.day) == (today.month, today.day):
        return True
    # Feb 29 birthdays are celebrated on Feb 28 in non-leap years.
    leap = today.year % 4 == 0 and (today.year % 100 != 0 or today.year % 400 == 0)
    return (
        (birthday.month, birthday.day) == (2, 29)
        and not leap
        and (today.month, today.day) == (2, 28)
    )


async def ensure_goal_contacts(
    session: AsyncSession, user_id: uuid.UUID, goal: Goal, pack: Pack
) -> dict[uuid.UUID, GoalContact]:
    """One goal_contacts row per contact. The deterministic label (target company) follows the
    goal's current companies; LLM labels on other contacts are kept. Changes are batched."""
    contacts = (
        await session.execute(
            select(Contact.id, Contact.company_norm).where(
                Contact.user_id == user_id, Contact.deleted_at.is_(None)
            )
        )
    ).all()
    targets = target_norms(pack, goal.params)
    det = (pack.relevance.get("deterministic") or {}).get("label")
    existing = {
        gc.contact_id: gc
        for gc in await session.scalars(
            select(GoalContact).where(
                GoalContact.goal_id == goal.id, GoalContact.user_id == user_id
            )
        )
    }
    new_rows = []
    for contact_id, company_norm in contacts:
        label = deterministic_label(pack, company_norm, targets)
        gc = existing.get(contact_id)
        if gc is None:
            new_rows.append(
                {
                    "goal_id": goal.id,
                    "contact_id": contact_id,
                    "user_id": user_id,
                    "relevance_label": label,
                    "relevance": weight(pack, label) if label else None,
                }
            )
        elif label is not None and gc.relevance_label != label:
            gc.relevance_label, gc.relevance = label, weight(pack, label)
        elif label is None and det is not None and gc.relevance_label == det:
            gc.relevance_label, gc.relevance = None, None  # no longer a target company
    await session.flush()
    if new_rows:
        await session.execute(insert(GoalContact).values(new_rows).on_conflict_do_nothing())
        for gc in await session.scalars(
            select(GoalContact).where(
                GoalContact.goal_id == goal.id,
                GoalContact.user_id == user_id,
                GoalContact.contact_id.in_([r["contact_id"] for r in new_rows]),
            )
        ):
            existing[gc.contact_id] = gc
    return existing


async def gather_signals(
    session: AsyncSession,
    user_id: uuid.UUID,
    goal: Goal,
    pack: Pack,
    today: date,
    goal_contacts: dict[uuid.UUID, GoalContact],
) -> tuple[list[Signals], dict[str, str | None]]:
    contacts = list(
        await session.scalars(
            select(Contact).where(Contact.user_id == user_id, Contact.deleted_at.is_(None))
        )
    )
    stage_role = {s.id: s.role for s in pack.stages}
    per_contact: dict[uuid.UUID, dict[str, Any]] = defaultdict(
        lambda: {"weighted": 0, "last": None, "last_sent": None}
    )
    for i in await session.scalars(select(Interaction).where(Interaction.user_id == user_id)):
        d = i.occurred_at.date()
        info = per_contact[i.contact_id]
        info["weighted"] += 2 if i.type in ("met", "replied") else 1
        info["last"] = max(filter(None, [info["last"], d]))
        if i.type == "sent":
            info["last_sent"] = max(filter(None, [info["last_sent"], d]))
            role = stage_role.get(i.stage or "")
            if role:
                key = f"last_{role}"
                info[key] = max(filter(None, [info.get(key), d]))
        elif i.type == "no_reply":
            info["last_no_reply"] = max(filter(None, [info.get("last_no_reply"), d]))
        elif i.type == "met":
            info["last_met"] = max(filter(None, [info.get("last_met"), d]))

    horizon = today - timedelta(days=int(pack.timing_boosts.get("job_change_days", 30)))
    job_changes: dict[uuid.UUID, date] = {}
    for t in await session.scalars(
        select(Trigger).where(
            Trigger.user_id == user_id, Trigger.type == "job_change", Trigger.date >= horizon
        )
    ):
        job_changes[t.contact_id] = max(t.date, job_changes.get(t.contact_id, t.date))

    snoozed: dict[uuid.UUID, date] = {}
    for s in await session.scalars(
        select(Suggestion).where(
            Suggestion.user_id == user_id,
            Suggestion.status == "snoozed",
            Suggestion.snoozed_until > today,
        )
    ):
        if s.snoozed_until:
            snoozed[s.contact_id] = max(s.snoozed_until, snoozed.get(s.contact_id, s.snoozed_until))

    signals: list[Signals] = []
    company_of: dict[str, str | None] = {}
    targets = target_norms(pack, goal.params)
    for c in contacts:
        gc = goal_contacts.get(c.id)
        info = per_contact.get(c.id, {})
        signals.append(
            Signals(
                contact_id=str(c.id),
                company_norm=c.company_norm,
                has_phone=bool(c.phones),
                has_linkedin=c.linkedin_url is not None,
                relevance_label=gc.relevance_label if gc else None,
                state=gc.state if gc else "none",
                thanked=bool(gc and gc.thanked_at),
                weighted_interactions=int(info.get("weighted", 0)),
                last_interaction=info.get("last"),
                last_sent=info.get("last_sent"),
                last_reconnect_sent=info.get("last_reconnect"),
                last_ask_sent=info.get("last_ask"),
                last_follow_up_sent=info.get("last_follow_up"),
                last_no_reply=info.get("last_no_reply"),
                last_met=info.get("last_met"),
                birthday_today=_birthday_today(c.birthday, today),
                job_change=job_changes.get(c.id),
                snoozed_until=snoozed.get(c.id),
                dismissed=bool(gc and gc.dismissed_at),
            )
        )
        # Group "Razorpay" and "Razorpay Software Pvt Ltd" as one company for the daily cap.
        company_of[str(c.id)] = matching_target(c.company_norm, targets) or c.company_norm
    return signals, company_of


def _reasons_json(scored: Scored) -> list[dict[str, Any]]:
    return [{"text": r.text, "highlight": r.highlight} for r in scored.reasons]


async def rank(
    session: AsyncSession, user_id: uuid.UUID, goal: Goal, pack: Pack, today: date, for_date: date
) -> int:
    """Rebuild the pending list for `for_date`. Keeps forced (dated) and already-acted items."""
    goal_contacts = await ensure_goal_contacts(session, user_id, goal, pack)
    signals, company_of = await gather_signals(session, user_id, goal, pack, today, goal_contacts)

    festival = await session.scalar(
        select(CalendarEvent.name).where(
            CalendarEvent.date == today, CalendarEvent.active.is_(True)
        )
    )
    det = (pack.relevance.get("deterministic") or {}).get("label")

    # Drop unacted, unforced suggestions for this date; expire older pending ones.
    existing = list(
        await session.scalars(
            select(Suggestion).where(Suggestion.user_id == user_id, Suggestion.for_date == for_date)
        )
    )
    for s in existing:
        if s.status == "pending" and not is_forced(s):
            await session.delete(s)
    await session.flush()
    await session.execute(
        update(Suggestion)
        .where(
            Suggestion.user_id == user_id,
            Suggestion.for_date < for_date,
            Suggestion.status.in_(["pending", "opened"]),
        )
        .values(status="expired")
    )
    kept = [s for s in existing if s.status != "pending" or is_forced(s)]
    taken = {str(s.contact_id) for s in kept}

    scored = [
        item
        for sig in signals
        if sig.contact_id not in taken
        and (item := score(sig, pack, today, festival_name=festival, deterministic_label=det))
    ]
    chosen = select_daily(
        scored,
        pack,
        company_of=company_of,
        already=len([s for s in kept if s.status != "dismissed"]),
        already_companies=[company_of.get(str(s.contact_id)) for s in kept],
    )
    if chosen:
        await session.execute(
            insert(Suggestion)
            .values(
                [
                    {
                        "user_id": user_id,
                        "goal_id": goal.id,
                        "contact_id": uuid.UUID(c.signals.contact_id),
                        "for_date": for_date,
                        "score": c.score,
                        "reasons": _reasons_json(c),
                        "stage": c.stage.id,
                    }
                    for c in chosen
                ]
            )
            .on_conflict_do_nothing()
        )
    return len(chosen)


async def add_thank_suggestion(
    session: AsyncSession,
    user_id: uuid.UUID,
    goal: Goal,
    pack: Pack,
    contact_id: uuid.UUID,
    day: date,
) -> None:
    """After an outcome: a thank-you appears today, skipping fatigue (FR-REP-2)."""
    thank = pack.stage_for("thank")
    stmt = insert(Suggestion).values(
        user_id=user_id,
        goal_id=goal.id,
        contact_id=contact_id,
        for_date=day,
        score=1.0,
        reasons=[{"text": "Say thanks", "highlight": True}],
        stage=thank.id,
    )
    await session.execute(
        stmt.on_conflict_do_update(
            index_elements=["user_id", "contact_id", "for_date"],
            set_={"stage": thank.id, "status": "pending", "reasons": stmt.excluded.reasons},
        )
    )


async def has_list(session: AsyncSession, user_id: uuid.UUID, for_date: date) -> bool:
    found = await session.scalar(
        select(Suggestion.id)
        .where(and_(Suggestion.user_id == user_id, Suggestion.for_date == for_date))
        .limit(1)
    )
    return found is not None
