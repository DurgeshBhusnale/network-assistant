"""Integration tests: Supabase Postgres (cloud dev project locally, CLI stack in CI) and Redis.

Every DB test runs in a transaction that is rolled back, so the dev project is left unchanged.
"""

import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.core.config import Settings, get_settings


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if "tests/integration" in item.nodeid.replace("\\", "/"):
            item.add_marker(pytest.mark.integration)


@pytest.fixture
def live_settings() -> Settings:
    return get_settings().model_copy(update={"app_env": "test", "ai_mode": "fake"})


@pytest.fixture
async def engine(live_settings: Settings) -> AsyncIterator[AsyncEngine]:
    eng = create_async_engine(live_settings.database_url)
    yield eng
    await eng.dispose()


@pytest.fixture
async def conn(engine: AsyncEngine) -> AsyncIterator[AsyncConnection]:
    """A connection inside a transaction that is always rolled back."""
    async with engine.connect() as connection:
        transaction = await connection.begin()
        try:
            yield connection
        finally:
            await transaction.rollback()


CreateUser = Callable[[], Awaitable[uuid.UUID]]


@pytest.fixture
def create_user(conn: AsyncConnection) -> CreateUser:
    async def _create() -> uuid.UUID:
        user_id = uuid.uuid4()
        await conn.execute(
            text(
                "insert into auth.users (id, email, aud, role) "
                "values (:id, :email, 'authenticated', 'authenticated')"
            ),
            {"id": user_id, "email": f"{user_id.hex}@example.test"},
        )
        await conn.execute(text("insert into profiles (user_id) values (:id)"), {"id": user_id})
        return user_id

    return _create


async def act_as(conn: AsyncConnection, user_id: uuid.UUID) -> None:
    """Switch the current transaction to the authenticated role with this user's JWT claims."""
    claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
    await conn.execute(text("set local role authenticated"))
    await conn.execute(text("select set_config('request.jwt.claims', :c, true)"), {"c": claims})


async def scalar(conn: AsyncConnection, sql: str, **params: Any) -> Any:
    return (await conn.execute(text(sql), params)).scalar_one()
