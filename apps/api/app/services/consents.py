"""Consent checks at call time (CLAUDE.md: respect consents before import, voice, WhatsApp)."""

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.errors import AppError, ErrorCode
from app.domain.models import Consent


async def has_consent(session: AsyncSession, user_id: uuid.UUID, kind: str) -> bool:
    found = await session.scalar(
        select(Consent.id)
        .where(Consent.user_id == user_id, Consent.type == kind, Consent.withdrawn_at.is_(None))
        .limit(1)
    )
    return found is not None


async def require_consent(
    session: AsyncSession, user_id: uuid.UUID, kind: str, message: str
) -> None:
    if not await has_consent(session, user_id, kind):
        raise AppError(ErrorCode.CONSENT_REQUIRED, message, 403)
