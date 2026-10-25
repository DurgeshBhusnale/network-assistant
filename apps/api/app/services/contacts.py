"""People: list/search, person page aggregate, create, update, delete (FR-CON-4/8/9, FR-PER-*)."""

import base64
import json
import uuid
from datetime import datetime

from sqlalchemy import column, delete, func, or_, select, table
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.domain.models import Contact, Goal, Interaction, Memory, Pack, Trigger
from app.domain.schemas import (
    ContactList,
    ContactSummary,
    HistoryItem,
    MemoryOut,
    NextStep,
    PersonOut,
)
from app.imports.normalise import (
    normalise_company,
    normalise_email,
    normalise_linkedin,
    normalise_phone,
)

PAGE_SIZE = 50

# Tables without ORM models yet (Sprints 3-4); only their contact/user columns are needed here.
_suggestions = table("suggestions", column("contact_id"), column("user_id"))
_goal_contacts = table("goal_contacts", column("contact_id"), column("user_id"))
_drafts = table("drafts", column("contact_id"), column("user_id"))


def _not_found() -> AppError:
    return AppError(ErrorCode.NOT_FOUND, "Person not found.", 404)


def _encode_cursor(name: str, contact_id: uuid.UUID) -> str:
    raw = json.dumps([name, str(contact_id)]).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _decode_cursor(cursor: str) -> tuple[str, uuid.UUID]:
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        name, contact_id = json.loads(base64.urlsafe_b64decode(padded))
        return str(name), uuid.UUID(contact_id)
    except (ValueError, TypeError) as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Invalid cursor.", 422) from exc


def _like(q: str) -> str:
    escaped = q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
    return f"%{escaped}%"


def summary(c: Contact) -> ContactSummary:
    return ContactSummary(
        id=c.id,
        full_name=c.full_name,
        title=c.title,
        company=c.company,
        city=c.city,
        how_known=c.how_known,
        has_phone=bool(c.phones),
        has_linkedin=c.linkedin_url is not None,
    )


async def list_contacts(
    session: AsyncSession, user_id: uuid.UUID, q: str | None, cursor: str | None
) -> ContactList:
    sort_key = func.lower(Contact.full_name)
    stmt = select(Contact).where(Contact.user_id == user_id, Contact.deleted_at.is_(None))
    if q and q.strip():
        pattern = _like(q.strip())
        stmt = stmt.where(or_(Contact.full_name.ilike(pattern), Contact.company.ilike(pattern)))
    if cursor:
        name, last_id = _decode_cursor(cursor)
        stmt = stmt.where(or_(sort_key > name, (sort_key == name) & (Contact.id > last_id)))
    rows = list(await session.scalars(stmt.order_by(sort_key, Contact.id).limit(PAGE_SIZE + 1)))
    has_more = len(rows) > PAGE_SIZE
    rows = rows[:PAGE_SIZE]
    next_cursor = (
        _encode_cursor(rows[-1].full_name.lower(), rows[-1].id) if has_more and rows else None
    )
    return ContactList(items=[summary(c) for c in rows], next_cursor=next_cursor)


async def get_contact(session: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID) -> Contact:
    contact = await session.scalar(
        select(Contact).where(
            Contact.id == contact_id, Contact.user_id == user_id, Contact.deleted_at.is_(None)
        )
    )
    if contact is None:
        raise _not_found()
    return contact


async def person(session: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID) -> PersonOut:
    c = await get_contact(session, user_id, contact_id)
    memories = await session.scalars(
        select(Memory)
        .where(Memory.contact_id == c.id, Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .limit(100)
    )
    interactions = await session.scalars(
        select(Interaction)
        .where(Interaction.contact_id == c.id, Interaction.user_id == user_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(100)
    )
    history = [
        HistoryItem(
            kind=i.type,
            channel=i.channel,
            stage=i.stage,
            outcome=i.outcome,
            occurred_at=i.occurred_at,
        )
        for i in interactions
    ]
    history.append(HistoryItem(kind="added", sources=c.sources, occurred_at=c.created_at))

    next_step = None
    goal = await session.scalar(
        select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
    )
    if goal is not None:
        pack = await session.scalar(select(Pack).where(Pack.id == goal.pack_id))
        label = (pack.config.get("copy", {}).get("goal_strip_label") if pack else None) or "Goal"
        next_step = NextStep(goal_label=label, stage=None, stage_label=None)

    return PersonOut(
        id=c.id,
        full_name=c.full_name,
        first_name=c.first_name,
        last_name=c.last_name,
        phones=c.phones,
        emails=c.emails,
        linkedin_url=c.linkedin_url,
        company=c.company,
        title=c.title,
        city=c.city,
        how_known=c.how_known,
        birthday=c.birthday,
        sources=c.sources,
        memories=[
            MemoryOut(id=m.id, text=m.text, source=m.source, created_at=m.created_at)
            for m in memories
        ],
        history=history,
        next_step=next_step,
    )


def _invalid(field: str) -> AppError:
    return AppError(ErrorCode.VALIDATION_ERROR, f"Check this field: {field}", 422)


def normalised_phones(values: list[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        if not raw.strip():
            continue
        phone = normalise_phone(raw)
        if phone is None:
            raise _invalid("phone")
        if phone not in result:
            result.append(phone)
    return result


def normalised_emails(values: list[str]) -> list[str]:
    result: list[str] = []
    for raw in values:
        if not raw.strip():
            continue
        email = normalise_email(raw)
        if email is None:
            raise _invalid("email")
        if email not in result:
            result.append(email)
    return result


def normalised_linkedin(raw: str | None) -> str | None:
    if raw is None or not raw.strip():
        return None
    url = normalise_linkedin(raw)
    if url is None:
        raise _invalid("linkedin_url")
    return url


async def find_duplicate(
    session: AsyncSession,
    user_id: uuid.UUID,
    phones: list[str],
    emails: list[str],
    linkedin_url: str | None,
    exclude: uuid.UUID | None = None,
) -> Contact | None:
    conditions = []
    if phones:
        conditions.append(Contact.phones.overlap(phones))
    if emails:
        conditions.append(Contact.emails.overlap(emails))
    if linkedin_url:
        conditions.append(Contact.linkedin_url == linkedin_url)
    if not conditions:
        return None
    stmt = select(Contact).where(
        Contact.user_id == user_id, Contact.deleted_at.is_(None), or_(*conditions)
    )
    if exclude is not None:
        stmt = stmt.where(Contact.id != exclude)
    return await session.scalar(stmt.limit(1))


def duplicate_error(existing: Contact) -> AppError:
    return AppError(
        ErrorCode.CONTACT_EXISTS, f"{existing.full_name} is already in your people.", 409
    )


def company_norm(company: str | None) -> str | None:
    return normalise_company(company)


async def delete_contact(
    session: AsyncSession, user_id: uuid.UUID, contact_id: uuid.UUID, now: datetime
) -> None:
    """Hides the person now and hard-deletes everything about them; the row is purged later."""
    contact = await get_contact(session, user_id, contact_id)
    for model in (Memory, Interaction, Trigger):
        await session.execute(
            delete(model).where(model.contact_id == contact.id, model.user_id == user_id)
        )
    for t in (_suggestions, _goal_contacts, _drafts):
        await session.execute(delete(t).where(t.c.contact_id == contact.id, t.c.user_id == user_id))
    contact.deleted_at = now
    await session.flush()
