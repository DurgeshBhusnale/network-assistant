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
    await track_many(engine, user_id, [(name, props or {})])


async def track_many(
    engine: AsyncEngine, user_id: uuid.UUID, events: list[tuple[str, dict[str, Any]]]
) -> None:
    """Several events in one session and one consent check."""
    if not events:
        return
    try:
        async with service_session(engine) as session:
            consented = await session.scalar(
                select(Consent.id)
                .where(
                    Consent.user_id == user_id,
                    Consent.type == "analytics",
                    Consent.withdrawn_at.is_(None),
                )
                .limit(1)
            )
            if consented is None:
                return
            session.add_all(Event(user_id=user_id, name=n, props=p) for n, p in events)
    except Exception as exc:
        logger.warning(
            "analytics_failed",
            extra={"event": events[0][0], "error_type": type(exc).__name__},
        )
