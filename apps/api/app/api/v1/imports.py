"""Imports (FR-CON-1/2/3/5/7): stage a preview, then commit."""

import uuid
from typing import Annotated

from fastapi import APIRouter, File, UploadFile
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.track import track
from app.api.v1.deps import ClockDep
from app.core.auth import CurrentUser
from app.core.clock import local_today
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.domain.models import ImportJob
from app.domain.schemas import ImportOut, PickerImport
from app.imports.models import ImportSource, ParseResult
from app.imports.parsers import ImportFileError, parse_linkedin_csv, parse_picker, parse_vcard
from app.services.consents import require_consent
from app.services.imports import commit_import, import_out, stage_import
from app.services.profiles import ensure_profile

router = APIRouter(prefix="/imports", tags=["imports"])

MAX_FILE_BYTES = 5 * 1024 * 1024
CONSENT_MESSAGE = "Allow contact import in Settings → Privacy first."


def _decode(data: bytes) -> str:
    for encoding in ("utf-8-sig", "utf-16"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("cp1252", errors="replace")  # Excel-saved CSVs on Windows


def _file_error(message: str) -> AppError:
    return AppError(ErrorCode.IMPORT_FILE_INVALID, message, 422)


async def _stage(
    engine: Engine, user: CurrentUser, source: ImportSource, parsed: ParseResult
) -> ImportOut:
    async with user_session(engine, user) as session:
        await require_consent(session, user.id, "contacts", CONSENT_MESSAGE)
        job = await stage_import(session, user.id, source, parsed)
        return import_out(job)


@router.post("/picker", response_model=ImportOut, status_code=201)
async def import_picker(body: PickerImport, user: CurrentUser, engine: Engine) -> ImportOut:
    parsed = parse_picker([c.model_dump() for c in body.contacts])
    return await _stage(engine, user, "picker", parsed)


@router.post("/file", response_model=ImportOut, status_code=201)
async def import_file(
    file: Annotated[UploadFile, File(description=".vcf or LinkedIn Connections.csv")],
    user: CurrentUser,
    engine: Engine,
) -> ImportOut:
    data = await file.read(MAX_FILE_BYTES + 1)
    if len(data) > MAX_FILE_BYTES:
        raise _file_error("That file is over 5 MB.")
    text = _decode(data)
    name = (file.filename or "").lower()
    is_vcard = name.endswith((".vcf", ".vcard")) or text.lstrip().upper().startswith("BEGIN:VCARD")
    try:
        if is_vcard:
            source: ImportSource = "vcard"
            parsed = parse_vcard(text)
        else:
            source = "linkedin_csv"
            parsed = parse_linkedin_csv(text)
    except ImportFileError as exc:
        raise _file_error(str(exc)) from exc
    return await _stage(engine, user, source, parsed)


async def _job(session: AsyncSession, user_id: uuid.UUID, import_id: uuid.UUID) -> ImportJob:
    job = await session.scalar(
        select(ImportJob).where(ImportJob.id == import_id, ImportJob.user_id == user_id)
    )
    if job is None:
        raise AppError(ErrorCode.NOT_FOUND, "Import not found.", 404)
    return job


@router.get("/{import_id}", response_model=ImportOut)
async def get_import(import_id: uuid.UUID, user: CurrentUser, engine: Engine) -> ImportOut:
    async with user_session(engine, user) as session:
        return import_out(await _job(session, user.id, import_id))


@router.post("/{import_id}/commit", response_model=ImportOut)
async def commit(
    import_id: uuid.UUID, user: CurrentUser, engine: Engine, clock: ClockDep
) -> ImportOut:
    async with user_session(engine, user) as session:
        await require_consent(session, user.id, "contacts", CONSENT_MESSAGE)
        profile = await ensure_profile(session, user)
        job = await _job(session, user.id, import_id)
        already = job.status == "committed"
        job = await commit_import(session, user.id, job, local_today(clock, profile.timezone))
        result = import_out(job)
    if not already:
        await track(
            engine,
            user.id,
            "contacts_imported",
            {
                "source": result.source,
                "count": result.counts.new,
                "duplicates": result.counts.merged,
            },
        )
    return result
