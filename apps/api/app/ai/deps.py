"""AI router construction and the route dependency."""

import logging
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.ext.asyncio import AsyncEngine

from app.ai.factory import LiveProvidersUnavailableError, build_providers
from app.ai.router import AIRouter
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)


def build_router(settings: Settings, engine: AsyncEngine) -> AIRouter | None:
    try:
        return AIRouter(settings, build_providers(settings).llm, engine)
    except LiveProvidersUnavailableError as exc:
        logger.error("ai_router_unavailable", extra={"reason": str(exc)})
        return None


def get_ai_router(request: Request) -> AIRouter:
    router: AIRouter | None = getattr(request.app.state, "ai_router", None)
    if router is None:
        raise AppError(ErrorCode.AI_UNAVAILABLE, "Drafting is unavailable right now.", 503)
    return router


AIRouterDep = Annotated[AIRouter, Depends(get_ai_router)]
