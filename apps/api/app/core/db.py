"""Database engine and sessions.

- `user_session(user)`: a transaction running as the `authenticated` role with the user's JWT
  claims, so RLS applies (tech spec §5.1). Use for every user request.
- `service_session()`: a transaction as the connection owner (bypasses RLS). Workers, webhooks
  and server-only tables (events, ai_calls, audit_log) only; always filter by user_id explicitly.
"""

import json
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Annotated

from fastapi import Depends, Request
from sqlalchemy import text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from app.core.config import Settings

if TYPE_CHECKING:
    from app.core.auth import AuthUser

logger = logging.getLogger(__name__)


def create_engine(settings: Settings) -> AsyncEngine:
    # No pre-ping: it costs a round trip per checkout (slow to a remote DB). Recycle instead.
    # pool_timeout: a request starved of connections fails fast instead of hanging.
    return create_async_engine(
        settings.database_url,
        pool_recycle=300,
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout_seconds,
    )


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


def get_engine(request: Request) -> AsyncEngine:
    engine: AsyncEngine = request.app.state.db_engine
    return engine


Engine = Annotated[AsyncEngine, Depends(get_engine)]


@asynccontextmanager
async def user_session(engine: AsyncEngine, user: "AuthUser") -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        # One round trip: SET LOCAL ROLE + the JWT claims that auth.uid() reads.
        await session.execute(
            text(
                "select set_config('role', 'authenticated', true), "
                "set_config('request.jwt.claims', :claims, true)"
            ),
            {"claims": json.dumps(user.claims)},
        )
        yield session


@asynccontextmanager
async def service_session(engine: AsyncEngine) -> AsyncIterator[AsyncSession]:
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as session, session.begin():
        yield session
