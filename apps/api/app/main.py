"""FastAPI app factory. Run with `uvicorn --factory app.main:create_app`."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.ai.deps import build_router
from app.api.v1 import router as v1_router
from app.core.config import Settings, get_settings
from app.core.db import create_engine, warm_db_pool
from app.core.errors import ErrorResponse, register_error_handlers
from app.core.logging import setup_logging
from app.core.redis import create_redis
from app.core.sentry import init_sentry


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    setup_logging(settings.log_level)
    init_sentry(settings)

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        app.state.db_engine = create_engine(settings)
        app.state.redis = create_redis(settings)
        app.state.ai_router = build_router(settings, app.state.db_engine)
        await warm_db_pool(app.state.db_engine)
        try:
            yield
        finally:
            await app.state.redis.aclose()
            await app.state.db_engine.dispose()

    app = FastAPI(
        title="Networking Assistant API",
        version="0.1.0",
        lifespan=lifespan,
        responses={422: {"model": ErrorResponse}, 500: {"model": ErrorResponse}},
    )
    register_error_handlers(app)
    app.include_router(v1_router)
    return app
