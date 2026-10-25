"""Per-user rate limits in Redis (tech spec §6): fixed windows, fail open if Redis is down."""

import logging
from collections.abc import Awaitable, Callable

from fastapi import Depends, Request

from app.core.auth import AuthUser, get_current_user
from app.core.errors import AppError, ErrorCode

logger = logging.getLogger(__name__)

GENERAL_PER_MINUTE = 60


async def hit(request: Request, key: str, limit: int, window_seconds: int) -> bool:
    """True if this request is within the limit."""
    redis = getattr(request.app.state, "redis", None)
    if redis is None:
        return True
    try:
        count = await redis.incr(key)
        if count == 1:
            await redis.expire(key, window_seconds)
        return int(count) <= limit
    except Exception as exc:
        logger.warning("rate_limit_unavailable", extra={"error_type": type(exc).__name__})
        return True


def _too_many() -> AppError:
    return AppError(ErrorCode.RATE_LIMITED, "Too many requests. Please slow down a little.", 429)


def limit(name: str, per: int, window_seconds: int) -> Callable[..., Awaitable[None]]:
    """Route dependency: `dependencies=[Depends(limit("drafts", 20, 60))]`."""

    async def dependency(request: Request, user: AuthUser = Depends(get_current_user)) -> None:  # noqa: B008
        if not await hit(request, f"rl:{name}:{user.id}", per, window_seconds):
            raise _too_many()

    return dependency


async def general_limit(request: Request, user: AuthUser) -> None:
    if not await hit(request, f"rl:all:{user.id}", GENERAL_PER_MINUTE, 60):
        raise _too_many()
