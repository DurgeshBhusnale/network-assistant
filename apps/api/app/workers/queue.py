"""Enqueue background jobs from the API. Never breaks the request if Redis is unavailable."""

import logging
from typing import Any

from arq import create_pool
from arq.connections import ArqRedis, RedisSettings
from fastapi import Request

from app.core.config import Settings

logger = logging.getLogger(__name__)


async def create_queue(settings: Settings) -> ArqRedis | None:
    try:
        pool: ArqRedis = await create_pool(RedisSettings.from_dsn(settings.redis_url))
        return pool
    except Exception as exc:
        logger.warning("queue_unavailable", extra={"error_type": type(exc).__name__})
        return None


async def enqueue(request: Request, task: str, *args: Any) -> None:
    pool: ArqRedis | None = getattr(request.app.state, "queue", None)
    if pool is None:
        return
    try:
        await pool.enqueue_job(task, *args)
    except Exception as exc:
        logger.warning("enqueue_failed", extra={"task": task, "error_type": type(exc).__name__})
