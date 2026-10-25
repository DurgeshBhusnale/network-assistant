"""GET /v1/health: liveness plus database and Redis checks."""

import asyncio
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel

from app.core.db import ping_db
from app.core.redis import ping_redis

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])

CHECK_TIMEOUT_SECONDS = 2.0

CheckStatus = Literal["ok", "down"]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    db: CheckStatus
    redis: CheckStatus


@dataclass(frozen=True)
class HealthChecks:
    db: Callable[[], Awaitable[None]]
    redis: Callable[[], Awaitable[None]]


def get_health_checks(request: Request) -> HealthChecks:
    state = request.app.state
    return HealthChecks(db=lambda: ping_db(state.db_engine), redis=lambda: ping_redis(state.redis))


async def _run(name: str, check: Callable[[], Awaitable[None]]) -> CheckStatus:
    try:
        await asyncio.wait_for(check(), timeout=CHECK_TIMEOUT_SECONDS)
    except Exception as exc:
        logger.warning(
            "health_check_failed", extra={"check": name, "error_type": type(exc).__name__}
        )
        return "down"
    return "ok"


@router.get(
    "/health",
    response_model=HealthResponse,
    responses={503: {"model": HealthResponse, "description": "A dependency is down"}},
)
async def health(
    response: Response, checks: Annotated[HealthChecks, Depends(get_health_checks)]
) -> HealthResponse:
    db, redis = await asyncio.gather(_run("db", checks.db), _run("redis", checks.redis))
    healthy = db == "ok" and redis == "ok"
    if not healthy:
        response.status_code = 503
    return HealthResponse(status="ok" if healthy else "degraded", db=db, redis=redis)
