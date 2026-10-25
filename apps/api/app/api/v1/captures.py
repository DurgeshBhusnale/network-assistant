"""Capture endpoints (FR-MEM-2..7): signed upload, create, poll, confirm, discard."""

import uuid

from fastapi import APIRouter, Request
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.deps import AIRouterDep
from app.analytics.track import track
from app.api.v1.deps import ClockDep, SettingsDep
from app.core.auth import CurrentUser
from app.core.clock import local_today
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.core.storage import Storage, StorageError
from app.domain.models import Capture
from app.domain.schemas import (
    CaptureConfirm,
    CaptureCreate,
    CaptureOut,
    CaptureResult,
    UploadUrlIn,
    UploadUrlOut,
)
from app.services import billing
from app.services import captures as svc
from app.services.consents import require_consent
from app.services.contacts import get_contact
from app.services.profiles import ensure_profile
from app.workers.queue import enqueue

router = APIRouter(prefix="/captures", tags=["capture"])

VOICE_CONSENT = "Allow voice processing in Settings → Privacy to record notes."
EXTENSIONS = {
    "audio/webm": "webm",
    "audio/ogg": "ogg",
    "audio/mp4": "m4a",
    "audio/mpeg": "mp3",
    "audio/wav": "wav",
    "audio/aac": "aac",
}


async def _capture(session: AsyncSession, user_id: uuid.UUID, capture_id: uuid.UUID) -> Capture:
    capture = await session.scalar(
        select(Capture).where(Capture.id == capture_id, Capture.user_id == user_id)
    )
    if capture is None:
        raise AppError(ErrorCode.NOT_FOUND, "Capture not found.", 404)
    return capture


@router.post("/upload-url", response_model=UploadUrlOut)
async def upload_url(
    body: UploadUrlIn, user: CurrentUser, engine: Engine, settings: SettingsDep
) -> UploadUrlOut:
    async with user_session(engine, user) as session:
        await require_consent(session, user.id, "voice", VOICE_CONSENT)
    path = f"{user.id}/{uuid.uuid4().hex}.{EXTENSIONS[body.mime]}"
    try:
        url = await Storage(settings).signed_upload_url(path)
    except StorageError as exc:
        raise AppError(
            ErrorCode.STORAGE_UNAVAILABLE, "Couldn't start the upload. Try again.", 503
        ) from exc
    return UploadUrlOut(upload_url=url, storage_path=path)


@router.post("", response_model=CaptureOut, status_code=201)
async def create_capture(
    body: CaptureCreate,
    request: Request,
    user: CurrentUser,
    engine: Engine,
    settings: SettingsDep,
    ai: AIRouterDep,
) -> CaptureOut:
    if (body.text is None) == (body.storage_path is None):
        raise AppError(ErrorCode.VALIDATION_ERROR, "Send either text or storage_path.", 422)
    async with user_session(engine, user) as session:
        if body.storage_path is not None:
            await require_consent(session, user.id, "voice", VOICE_CONSENT)
            if not body.storage_path.startswith(f"{user.id}/") or ".." in body.storage_path:
                raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: storage_path", 422)
        if body.contact_id is not None:
            await get_contact(session, user.id, body.contact_id)
        capture = Capture(
            user_id=user.id,
            source="app_audio" if body.storage_path else "app_text",
            storage_path=body.storage_path,
            transcript=body.text.strip() if body.text else None,
            language=body.language_hint,
            extracted={"for_contact": str(body.contact_id)} if body.contact_id else None,
            status="queued",
        )
        session.add(capture)
        await session.flush()
        await session.refresh(capture)
        capture_id = capture.id
        result = svc.capture_out(capture)
    queue = getattr(request.app.state, "queue", None)
    if queue is not None:
        await enqueue(request, "process_capture", str(capture_id))
    else:  # no worker available (e.g. Redis down): process inline so capture still works
        await svc.process_capture(engine, ai, Storage(settings), capture_id)
        async with user_session(engine, user) as session:
            result = svc.capture_out(await _capture(session, user.id, capture_id))
    return result


@router.get("/{capture_id}", response_model=CaptureOut)
async def get_capture(capture_id: uuid.UUID, user: CurrentUser, engine: Engine) -> CaptureOut:
    async with user_session(engine, user) as session:
        return svc.capture_out(await _capture(session, user.id, capture_id))


@router.post("/{capture_id}/confirm", response_model=CaptureResult)
async def confirm_capture(
    capture_id: uuid.UUID,
    body: CaptureConfirm,
    request: Request,
    user: CurrentUser,
    engine: Engine,
    clock: ClockDep,
) -> CaptureResult:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        capture = await _capture(session, user.id, capture_id)
        plan = await billing.current_plan(session, user.id, clock.now())
        source = capture.source
        found_people = len((capture.extracted or {}).get("people", []))
        result = await svc.confirm(
            session, user.id, capture, body, local_today(clock, profile.timezone), plan.kind
        )
    if result.created:
        await enqueue(request, "label_relevance", str(user.id))
    await track(
        engine,
        user.id,
        "voice_captured",
        {
            "source": source,
            "people_found": found_people,
            "confirmed": result.created + result.merged,
        },
    )
    return result


@router.post("/{capture_id}/discard", status_code=204)
async def discard_capture(capture_id: uuid.UUID, user: CurrentUser, engine: Engine) -> None:
    async with user_session(engine, user) as session:
        svc.discard(await _capture(session, user.id, capture_id))
