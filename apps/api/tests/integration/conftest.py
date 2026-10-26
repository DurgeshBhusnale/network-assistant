"""Integration tests: Supabase Postgres (cloud dev project locally, CLI stack in CI) and Redis.

SQL-level tests run in a transaction that is rolled back. API tests (`users`, `anon`) run the
real app and commit, so each throwaway user and everything they own is deleted afterwards.
Either way the dev project is left as it was.
"""

import json
import uuid
from collections.abc import AsyncIterator, Awaitable, Callable
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from pydantic import SecretStr
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

from app.core.config import Settings, get_settings
from app.main import create_app
from tests.integration.api import (
    TEST_JWT_SECRET,
    UNSUBSCRIBE_SECRET,
    WA_VERIFY_TOKEN,
    WEBHOOK_SECRET,
    User,
    delete_users,
    insert_auth_user,
    mint_token,
)


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


@pytest.fixture(scope="session")
async def api_app() -> AsyncIterator[FastAPI]:
    """The real app (dev project, Redis, fake AI), started once. Jobs are not queued: tests run
    worker functions directly when they need them."""
    settings = get_settings().model_copy(
        update={
            "app_env": "test",
            "ai_mode": "fake",
            "sentry_dsn": None,
            "supabase_jwt_secret": SecretStr(TEST_JWT_SECRET),
            "razorpay_key_id": "",
            "razorpay_key_secret": None,
            "razorpay_webhook_secret": SecretStr(WEBHOOK_SECRET),
            "wa_app_secret": SecretStr(WEBHOOK_SECRET),
            "wa_verify_token": SecretStr(WA_VERIFY_TOKEN),
            "wa_access_token": None,  # dry run: nothing reaches Meta
            "wa_display_number": "919800000000",
            "wa_briefs_enabled": True,
            "unsubscribe_secret": SecretStr(UNSUBSCRIBE_SECRET),
            "admin_user_ids": "",
            # Leave pooler room for a running `pnpm dev` (see Settings.db_pool_size).
            "db_pool_size": 3,
            "db_max_overflow": 0,
        }
    )
    app = create_app(settings)
    async with app.router.lifespan_context(app):
        queue = app.state.queue
        app.state.queue = None
        try:
            yield app
        finally:
            app.state.queue = queue


@pytest.fixture
def api_engine(api_app: FastAPI) -> AsyncEngine:
    engine: AsyncEngine = api_app.state.db_engine
    return engine


MakeUser = Callable[[], Awaitable[User]]


@pytest.fixture
async def users(api_app: FastAPI, api_engine: AsyncEngine) -> AsyncIterator[MakeUser]:
    created: list[User] = []

    async def make() -> User:
        user_id, email = await insert_auth_user(api_engine)
        http = httpx.AsyncClient(
            transport=httpx.ASGITransport(app=api_app),
            base_url="http://test",
            headers={"Authorization": f"Bearer {mint_token(user_id, email)}"},
            timeout=60,
        )
        user = User(user_id, email, http)
        created.append(user)
        return user

    yield make
    for u in created:
        await u.http.aclose()
    await delete_users(api_engine, [u.id for u in created])


@pytest.fixture
async def anon(api_app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=api_app), base_url="http://test", timeout=60
    ) as client:
        yield client
