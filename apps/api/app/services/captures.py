"""Capture pipeline (tech spec §8.4): audio/text → transcript → extraction → candidates → confirm.

Privacy: audio is deleted right after transcription (audit row written); transcripts and
candidate text are cleared on confirm/discard; sweeps catch anything left behind (FR-MEM-5/7).
"""

import logging
import uuid
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.ai.prompts import render
from app.ai.router import AIRouter, AIUnavailableError
from app.core.db import service_session
from app.core.errors import AppError, ErrorCode
from app.core.storage import Storage, StorageError
from app.domain.models import (
    AuditLog,
    Capture,
    Contact,
    Interaction,
    Memory,
    Profile,
    Suggestion,
)
from app.domain.schemas import (
    CaptureCandidate,
    CaptureConfirm,
    CaptureMatch,
    CaptureOut,
    CaptureResult,
)
from app.engine.capture import (
    ExtractResult,
    KnownContact,
    build_candidates,
    memory_texts,
)
from app.imports.normalise import clean_text, normalise_company, split_name
from app.services import ranking
from app.services.loop import active_goal_and_pack

logger = logging.getLogger(__name__)

MAX_AUDIO_BYTES = 16 * 1024 * 1024
MEMORY_SOURCE = {
    "app_audio": "voice",
    "app_text": "note",
    "wa_audio": "whatsapp",
    "wa_text": "whatsapp",
}


def capture_out(c: Capture) -> CaptureOut:
    data = c.extracted or {}
    for_contact = data.get("for_contact")
    people = [
        CaptureCandidate(
            key=p["key"],
            full_name=p["full_name"],
            first_name=p.get("first_name"),
            last_name=p.get("last_name"),
            company=p.get("company"),
            title=p.get("title"),
            where_met=p.get("where_met"),
            facts=p.get("facts", []),
            commitments=p.get("commitments", []),
            follow_up_date=p.get("follow_up_date"),
            matches=[CaptureMatch(**m) for m in p.get("matches", [])],
        )
        for p in data.get("people", [])
    ]
    return CaptureOut(
        id=c.id,
        source=c.source,
        status=c.status,
        transcript=c.transcript if c.status == "ready" else None,
        people=people,
        unassigned_facts=list(data.get("unassigned_facts", [])),
        error=c.error,
        for_contact_id=uuid.UUID(for_contact) if for_contact else None,
    )


async def _known_contacts(session: AsyncSession, user_id: uuid.UUID) -> list[KnownContact]:
    rows = await session.execute(
        select(Contact.id, Contact.full_name, Contact.company_norm).where(
            Contact.user_id == user_id, Contact.deleted_at.is_(None)
        )
    )
    return [KnownContact(str(i), n, c) for i, n, c in rows]


async def _audit(
    session: AsyncSession, user_id: uuid.UUID, action: str, meta: dict[str, Any]
) -> None:
    session.add(AuditLog(user_ref=str(user_id), action=action, meta=meta))


async def _fail(engine: AsyncEngine, capture_id: uuid.UUID, code: str) -> None:
    async with service_session(engine) as session:
        await session.execute(
            update(Capture).where(Capture.id == capture_id).values(status="failed", error=code)
        )


async def process_capture(
    engine: AsyncEngine, router: AIRouter, storage: Storage, capture_id: uuid.UUID
) -> None:
    """Worker step. Every query is scoped by the capture's user_id (service session)."""
    async with service_session(engine) as session:
        capture = await session.get(Capture, capture_id)
        if capture is None or capture.status not in ("queued", "processing"):
            return
        capture.status = "processing"
        user_id = capture.user_id
        profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
        timezone = profile.timezone if profile else "Asia/Kolkata"
        created_at = capture.created_at
        storage_path, text, hint = capture.storage_path, capture.transcript, capture.language
        for_contact_id = (capture.extracted or {}).get("for_contact")

    if storage_path:
        try:
            audio, mime = await storage.download(storage_path, MAX_AUDIO_BYTES)
        except StorageError:
            await _fail(engine, capture_id, "audio_missing")
            return
        try:
            transcript = await router.transcribe(audio, mime, user_id=user_id, language_hint=hint)
        except AIUnavailableError:
            await _fail(engine, capture_id, "transcription_failed")
            return
        finally:
            del audio
        try:
            await storage.delete([storage_path])
            deleted = True
        except StorageError:
            deleted = False  # the hourly sweep retries
        async with service_session(engine) as session:
            await session.execute(
                update(Capture)
                .where(Capture.id == capture_id, Capture.user_id == user_id)
                .values(
                    transcript=transcript.text,
                    language=transcript.language,
                    storage_path=None if deleted else storage_path,
                    audio_deleted_at=datetime.now(ZoneInfo("UTC")) if deleted else None,
                )
            )
            if deleted:
                await _audit(session, user_id, "audio_deleted", {"capture_id": str(capture_id)})
        text = transcript.text

    if not text or not text.strip():
        await _fail(engine, capture_id, "no_speech")
        return

    local = created_at.astimezone(ZoneInfo(timezone))
    prompt = render(
        "extract_people.v1",
        capture_datetime_local=local.strftime("%A, %d %B %Y %H:%M"),
        timezone=timezone,
        note=text,
    )
    try:
        result, _ = await router.complete_json(
            "extract_people",
            "extract_people.v1",
            prompt,
            ExtractResult,
            user_id=user_id,
            temperature=0.0,
        )
    except AIUnavailableError:
        await _fail(engine, capture_id, "extraction_failed")
        return

    async with service_session(engine) as session:
        known = await _known_contacts(session, user_id)
        target = (
            next((k for k in known if k.contact_id == for_contact_id), None)
            if for_contact_id
            else None
        )
        extracted = build_candidates(result, known, local.date(), for_contact=target)
        if for_contact_id:
            extracted["for_contact"] = for_contact_id
        await session.execute(
            update(Capture)
            .where(Capture.id == capture_id, Capture.user_id == user_id)
            .values(extracted=extracted, status="ready", error=None)
        )


def _clear(capture: Capture, summary: dict[str, Any]) -> None:
    capture.transcript = None
    capture.extracted = summary
    capture.status = "committed"


async def confirm(
    session: AsyncSession,
    user_id: uuid.UUID,
    capture: Capture,
    body: CaptureConfirm,
    today: date,
    plan_kind: str,
) -> CaptureResult:
    """Applies the user's decisions in one transaction (FR-MEM-3/4)."""
    if capture.status != "ready":
        raise AppError(ErrorCode.CAPTURE_NOT_READY, "This capture isn't ready to save.", 409)
    candidates = {p["key"]: p for p in (capture.extracted or {}).get("people", [])}
    found = await active_goal_and_pack(session, user_id)
    goal, pack = found if found else (None, None)
    follow_stage = (pack.by_role("follow_up") or pack.stage_for("reconnect")) if pack else None
    source = MEMORY_SOURCE.get(capture.source, "note")
    created = merged = memories = follow_ups = 0
    contact_ids: list[uuid.UUID] = []

    for d in body.decisions:
        cand = candidates.get(d.key)
        if cand is None:
            raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: decisions.key", 422)
        if d.action == "discard":
            continue
        if d.action == "merge":
            if d.contact_id is None:
                raise AppError(
                    ErrorCode.VALIDATION_ERROR, "Check this field: decisions.contact_id", 422
                )
            contact = await session.scalar(
                select(Contact).where(
                    Contact.id == d.contact_id,
                    Contact.user_id == user_id,
                    Contact.deleted_at.is_(None),
                )
            )
            if contact is None:
                raise AppError(ErrorCode.NOT_FOUND, "Person not found.", 404)
            company = clean_text(d.company if d.company is not None else cand.get("company"))
            if company and not contact.company:
                contact.company, contact.company_norm = company, normalise_company(company)
            title = clean_text(d.title if d.title is not None else cand.get("title"))
            if title and not contact.title:
                contact.title = title
            merged += 1
        else:
            name = split_name(d.full_name or cand["full_name"])
            if name is None:
                raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: full_name", 422)
            company = clean_text(d.company if d.company is not None else cand.get("company"))
            contact = Contact(
                user_id=user_id,
                full_name=name[0],
                first_name=name[1],
                last_name=name[2],
                company=company,
                company_norm=normalise_company(company),
                title=clean_text(d.title if d.title is not None else cand.get("title")),
                how_known=f"Met at {cand['where_met']}" if cand.get("where_met") else None,
                sources=["manual"],
            )
            session.add(contact)
            await session.flush()
            created += 1
        contact_ids.append(contact.id)

        facts = d.facts if d.facts is not None else cand.get("facts", [])
        for text in memory_texts(facts, cand.get("commitments", []), cand.get("where_met")):
            session.add(Memory(user_id=user_id, contact_id=contact.id, text=text, source=source))
            memories += 1
        if not (capture.extracted or {}).get("for_contact"):
            session.add(
                Interaction(
                    user_id=user_id,
                    contact_id=contact.id,
                    goal_id=goal.id if goal else None,
                    type="met",
                    occurred_at=capture.created_at,
                    meta={"where": cand.get("where_met")} if cand.get("where_met") else {},
                )
            )
            contact.last_interaction_at = capture.created_at

        follow_up = d.follow_up_date or (
            date.fromisoformat(cand["follow_up_date"]) if cand.get("follow_up_date") else None
        )
        if follow_up and follow_stage is not None and follow_up >= today:
            for_date = ranking.week_start(follow_up) if plan_kind == "free" else follow_up
            reason = (
                f"Met at {cand['where_met']}"
                if cand.get("where_met")
                else "You planned to follow up"
            )
            stmt = insert(Suggestion).values(
                user_id=user_id,
                goal_id=goal.id if goal else None,
                contact_id=contact.id,
                for_date=for_date,
                score=1.0,
                reasons=[{"text": reason, "highlight": True, "kind": ranking.FORCED_KIND}],
                stage=follow_stage.id,
            )
            await session.execute(
                stmt.on_conflict_do_update(
                    index_elements=["user_id", "contact_id", "for_date"],
                    set_={
                        "stage": follow_stage.id,
                        "reasons": stmt.excluded.reasons,
                        "status": "pending",
                    },
                )
            )
            follow_ups += 1

    _clear(capture, {"confirmed": created + merged})
    await session.flush()
    return CaptureResult(
        created=created,
        merged=merged,
        memories=memories,
        follow_ups=follow_ups,
        contact_ids=contact_ids,
    )


def discard(capture: Capture) -> None:
    _clear(capture, {"discarded": True})


async def sweep_audio(engine: AsyncEngine, storage: Storage, now: datetime) -> int:
    """Hourly: delete any audio still stored an hour after upload (privacy checklist)."""
    async with service_session(engine) as session:
        rows = list(
            await session.scalars(
                select(Capture).where(
                    Capture.storage_path.is_not(None),
                    Capture.audio_deleted_at.is_(None),
                    Capture.created_at < now - timedelta(hours=1),
                )
            )
        )
        for c in rows:
            try:
                await storage.delete([c.storage_path or ""])
            except StorageError:
                continue
            c.storage_path = None
            c.audio_deleted_at = now
            await _audit(
                session, c.user_id, "audio_deleted", {"capture_id": str(c.id), "sweep": True}
            )
    return len(rows)


async def sweep_transcripts(engine: AsyncEngine, now: datetime) -> int:
    """Clear capture text not confirmed within 24 h (FR-MEM-7)."""
    async with service_session(engine) as session:
        result = await session.execute(
            update(Capture)
            .where(
                Capture.created_at < now - timedelta(hours=24),
                Capture.status.in_(["queued", "processing", "ready", "failed"]),
            )
            .values(transcript=None, extracted={"expired": True}, status="committed")
        )
        return int(result.rowcount or 0)  # type: ignore[attr-defined]
