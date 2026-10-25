"""Worker tasks. Feature tasks (ranking, captures, briefs) arrive with their sprints."""

import logging
from typing import Any

logger = logging.getLogger(__name__)


async def ping(_ctx: dict[str, Any], value: str) -> str:
    """Round-trip task used by tests and to check a worker is consuming the queue."""
    return value


async def heartbeat(_ctx: dict[str, Any]) -> None:
    """No-op cron: proves the scheduler runs."""
    logger.info("worker_heartbeat")
