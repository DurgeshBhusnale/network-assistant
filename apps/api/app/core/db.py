"""Database engine. Per-request RLS sessions (`user_session`) arrive in Sprint 1."""

import logging

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config import Settings


def create_engine(settings: Settings) -> AsyncEngine:
    return create_async_engine(settings.database_url, pool_pre_ping=True)


logger = logging.getLogger(__name__)


async def ping_db(engine: AsyncEngine) -> None:
    async with engine.connect() as conn:
        await conn.execute(text("select 1"))


async def warm_db_pool(engine: AsyncEngine) -> None:
    """Open the first pooled connection at startup (TLS + auth is the slow part), so the first
    request and health checks measure steady-state latency. Startup continues if the DB is down."""
    try:
        await ping_db(engine)
    except Exception as exc:
        logger.warning("db_warmup_failed", extra={"error_type": type(exc).__name__})
