"""Privacy notice acknowledgement and itemised consents (FR-ONB-3, FR-PRIV-1)."""

import typing
from datetime import datetime

from fastapi import APIRouter, Depends, Response
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.analytics.track import track
from app.api.v1.deps import ClockDep, SettingsDep
from app.core.auth import AuthUser, CurrentUser
from app.core.config import Settings
from app.core.db import Engine, user_session
from app.core.errors import AppError, ErrorCode
from app.core.ratelimit import limit
from app.domain.models import Consent
from app.domain.schemas import ConsentKind, ConsentsOut, ConsentState, ConsentsUpdate
from app.services import privacy
from app.services.profiles import ensure_profile

router = APIRouter(prefix="/privacy", tags=["privacy"])

CONSENT_KINDS: tuple[ConsentKind, ...] = typing.get_args(ConsentKind)


async def _active(session: AsyncSession, user: AuthUser) -> dict[str, Consent]:
    rows = await session.scalars(
        select(Consent)
        .where(Consent.user_id == user.id, Consent.withdrawn_at.is_(None))
        .order_by(Consent.granted_at)
    )
    return {c.type: c for c in rows}


def _out(active: dict[str, Consent], notice_accepted: bool, settings: Settings) -> ConsentsOut:
    return ConsentsOut(
        notice_version=settings.privacy_notice_version,
        notice_accepted=notice_accepted,
        consents={
            kind: ConsentState(
                granted=kind in active,
                version=active[kind].version if kind in active else None,
                granted_at=active[kind].granted_at if kind in active else None,
            )
            for kind in CONSENT_KINDS
        },
    )


@router.get("/consents", response_model=ConsentsOut)
async def get_consents(user: CurrentUser, engine: Engine, settings: SettingsDep) -> ConsentsOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        accepted = profile.privacy_notice_version == settings.privacy_notice_version
        return _out(await _active(session, user), accepted, settings)


@router.put("/consents", response_model=ConsentsOut)
async def update_consents(
    body: ConsentsUpdate,
    user: CurrentUser,
    engine: Engine,
    settings: SettingsDep,
    clock: ClockDep,
) -> ConsentsOut:
    if not body.accept_notice:
        raise AppError(
            ErrorCode.PRIVACY_NOTICE_REQUIRED, "Accept the privacy notice to continue.", 422
        )
    now: datetime = clock.now()
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        first_acceptance = profile.privacy_notice_version is None
        profile.privacy_notice_version = settings.privacy_notice_version
        profile.privacy_notice_ack_at = now

        active = await _active(session, user)
        for kind, granted in body.consents.items():
            current = active.get(kind)
            if granted and current is None:
                consent = Consent(
                    user_id=user.id, type=kind, version=settings.consent_version, granted_at=now
                )
                session.add(consent)
                active[kind] = consent
            elif not granted and current is not None:
                current.withdrawn_at = now
                del active[kind]
        await session.flush()
        result = _out(active, True, settings)
    if first_acceptance:
        await track(engine, user.id, "signup", {})
    return result


class DeleteAccountIn(BaseModel):
    confirm: str


@router.post("/export", response_class=Response, dependencies=[Depends(limit("export", 3, 3600))])
async def export_data(user: CurrentUser, engine: Engine, clock: ClockDep) -> Response:
    """FR-PRIV-2: a zip of everything we hold about you, streamed directly (no stored copy)."""
    data = await privacy.export_zip(engine, user.id)
    name = f"my-data-{clock.now():%Y%m%d}.zip"
    return Response(
        content=data,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{name}"',
            "Cache-Control": "no-store",
        },
    )


@router.post("/delete-account", status_code=202, dependencies=[Depends(limit("delete", 3, 3600))])
async def delete_account(
    body: DeleteAccountIn, user: CurrentUser, engine: Engine, settings: SettingsDep
) -> Response:
    """FR-PRIV-3: typed confirmation, then everything goes (payments kept anonymised for tax)."""
    if body.confirm.strip().upper() != "DELETE":
        raise AppError(ErrorCode.VALIDATION_ERROR, "Type DELETE to confirm.", 422)
    await privacy.delete_account(engine, settings, user.id)
    return Response(status_code=202)
