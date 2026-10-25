"""Server-side product analytics (tech spec §13). Only for users with analytics consent."""

import logging
import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.db import service_session
from app.domain.models import Consent, Event

logger = logging.getLogger(__name__)


async def track(
    engine: AsyncEngine, user_id: uuid.UUID, name: str, props: dict[str, Any] | None = None
) -> None:
    """Record an event. Never raises: analytics must not break the user's request."""
    try:
        async with service_session(engine) as session:
            consented = await session.scalar(
                select(Consent.id).where(
                    Consent.user_id == user_id,
                    Consent.type == "analytics",
                    Consent.withdrawn_at.is_(None),
                )
            )
            if consented is None:
                return
            session.add(Event(user_id=user_id, name=name, props=props or {}))
    except Exception as exc:
        logger.warning("analytics_failed", extra={"event": name, "error_type": type(exc).__name__})
