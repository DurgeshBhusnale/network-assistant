import uuid

import httpx
import pytest
from arq import create_pool
from arq.connections import RedisSettings
from arq.worker import Worker

from app.core.config import Settings
from app.main import create_app
from app.workers.tasks import ping


async def test_health_live_reports_db_and_redis_ok(live_settings: Settings) -> None:
    app = create_app(live_settings)
    async with app.router.lifespan_context(app):
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://test") as client:
            response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "redis": "ok"}


async def test_worker_runs_ping_task(live_settings: Settings) -> None:
    redis_settings = RedisSettings.from_dsn(live_settings.redis_url)
    queue = f"test:{uuid.uuid4().hex}"
    pool = await create_pool(redis_settings, default_queue_name=queue)
    try:
        job = await pool.enqueue_job("ping", "pong")
        assert job is not None
        worker = Worker(
            functions=[ping], redis_pool=pool, queue_name=queue, burst=True, poll_delay=0.05
        )
        await worker.main()
        assert await job.result(timeout=5) == "pong"
        await worker.close()
    finally:
        await pool.aclose()


async def test_supabase_data_api_is_disabled(live_settings: Settings) -> None:
    """ADR-0007: PostgREST must not serve the public schema, even with the anon key."""
    if live_settings.supabase_anon_key is None:
        pytest.fail("SUPABASE_ANON_KEY not set; `make test-int` exports it from `supabase status`")
    anon = live_settings.supabase_anon_key.get_secret_value()
    async with httpx.AsyncClient(base_url=live_settings.supabase_url, timeout=10) as client:
        response = await client.get(
            "/rest/v1/packs", headers={"apikey": anon, "Authorization": f"Bearer {anon}"}
        )

    assert response.status_code != 200
    assert "career_sprint" not in response.text
