"""arq worker settings. Run with `uv run arq app.workers.settings.WorkerSettings`."""

from typing import Any, ClassVar

from arq import cron
from arq.connections import RedisSettings

from app.ai.deps import build_router
from app.core.config import get_settings
from app.core.db import create_engine
from app.core.logging import setup_logging
from app.workers.tasks import label_relevance, ping, process_capture


async def startup(ctx: dict[str, Any]) -> None:
    settings = get_settings()
    setup_logging(settings.log_level)
    ctx["settings"] = settings
    ctx["engine"] = create_engine(settings)
    ctx["ai_router"] = build_router(settings, ctx["engine"])


async def shutdown(ctx: dict[str, Any]) -> None:
    await ctx["engine"].dispose()


class WorkerSettings:
    functions: ClassVar[list[Any]] = [ping, label_relevance, process_capture]
    cron_jobs: ClassVar[list[Any]] = [
        cron("app.workers.tasks.heartbeat", minute={0, 15, 30, 45}, run_at_startup=False),
        cron("app.workers.tasks.rank_due_users", minute={0, 15, 30, 45}, run_at_startup=False),
        cron("app.workers.tasks.sweep_captures", minute={5}, run_at_startup=False),
    ]
    on_startup = startup
    on_shutdown = shutdown
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
