"""Import flow (FR-CON-1..7): parse → stage a preview → commit. Commits are idempotent."""

import uuid
from datetime import date
from typing import Any, cast

from sqlalchemy import Table, bindparam, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.models import Contact, ImportJob, Trigger
from app.domain.schemas import ImportCounts, ImportOut, ImportRowError
from app.imports.dedupe import ContactFields, ExistingContact, ImportPlan, plan_import
from app.imports.models import Candidate, ImportSource, ParseResult

MAX_ERRORS_SHOWN = 200
_MERGE_COLUMNS = (
    "first_name",
    "last_name",
    "phones",
    "emails",
    "linkedin_url",
    "company",
    "company_norm",
    "title",
    "birthday",
    "sources",
)


async def existing_contacts(session: AsyncSession, user_id: uuid.UUID) -> list[ExistingContact]:
    rows = await session.execute(
        select(
            Contact.id,
            Contact.full_name,
            *(getattr(Contact, c) for c in _MERGE_COLUMNS),
        ).where(Contact.user_id == user_id, Contact.deleted_at.is_(None))
    )
    result = []
    for row in rows:
        data = row._asdict()
        contact_id = data.pop("id")
        data["phones"] = list(data["phones"] or [])
        data["emails"] = list(data["emails"] or [])
        data["sources"] = list(data["sources"] or [])
        result.append(ExistingContact(id=contact_id, fields=ContactFields(**data)))
    return result


def import_out(job: ImportJob) -> ImportOut:
    return ImportOut(
        id=job.id,
        source=job.source,
        status=job.status,
        counts=ImportCounts(**job.counts),
        errors=[ImportRowError(**e) for e in job.errors[:MAX_ERRORS_SHOWN]],
        created_at=job.created_at,
    )


def _counts(plan: ImportPlan, skipped: int) -> dict[str, int]:
    return {**plan.counts, "skipped": skipped}


async def stage_import(
    session: AsyncSession, user_id: uuid.UUID, source: ImportSource, parsed: ParseResult
) -> ImportJob:
    plan = plan_import(parsed.candidates, await existing_contacts(session, user_id))
    job = ImportJob(
        user_id=user_id,
        source=source,
        status="ready",
        counts=_counts(plan, len(parsed.errors)),
        errors=[e.model_dump() for e in parsed.errors],
        preview={"candidates": [c.model_dump(mode="json") for c in parsed.candidates]},
    )
    session.add(job)
    await session.flush()
    await session.refresh(job)
    return job


def _row(fields: ContactFields) -> dict[str, Any]:
    return {"full_name": fields.full_name, **{c: getattr(fields, c) for c in _MERGE_COLUMNS}}


async def commit_import(
    session: AsyncSession, user_id: uuid.UUID, job: ImportJob, today: date
) -> ImportJob:
    """Re-plans against current contacts (they may have changed since the preview)."""
    if job.status == "committed":
        return job
    candidates = [Candidate.model_validate(c) for c in (job.preview or {}).get("candidates", [])]
    plan = plan_import(candidates, await existing_contacts(session, user_id))

    if plan.new:
        await session.execute(
            insert(Contact), [{"user_id": user_id, **_row(n.fields)} for n in plan.new]
        )
    changed = [m for m in plan.merges if m.changed]
    if changed:
        table = cast(Table, Contact.__table__)
        await session.execute(
            update(table)
            .where(table.c.id == bindparam("_id"), table.c.user_id == user_id)
            .values({c: bindparam(f"v_{c}") for c in _MERGE_COLUMNS}),
            [
                {"_id": m.contact_id, **{f"v_{c}": getattr(m.fields, c) for c in _MERGE_COLUMNS}}
                for m in changed
            ],
        )
    job_changes = [m.contact_id for m in plan.merges if m.job_changed]
    if job_changes:
        await session.execute(
            insert(Trigger)
            .values(
                [
                    {"user_id": user_id, "contact_id": cid, "type": "job_change", "date": today}
                    for cid in job_changes
                ]
            )
            .on_conflict_do_nothing()
        )
    job.status = "committed"
    job.counts = _counts(plan, job.counts.get("skipped", 0))
    job.preview = None
    await session.flush()
    return job
