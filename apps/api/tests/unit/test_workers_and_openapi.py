import json
import logging

import pytest

from app.openapi_export import OPENAPI_PATH, render_openapi
from app.workers.settings import WorkerSettings
from app.workers.tasks import heartbeat, ping


async def test_ping_task_round_trips() -> None:
    assert await ping({}, "hello") == "hello"


async def test_heartbeat_cron_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="app.workers.tasks"):
        await heartbeat({})
    assert "worker_heartbeat" in caplog.messages


def test_worker_settings_register_tasks_and_cron() -> None:
    assert ping in WorkerSettings.functions
    assert [job.name for job in WorkerSettings.cron_jobs] == ["cron:app.workers.tasks.heartbeat"]


def test_openapi_lists_health_with_error_envelope() -> None:
    spec = json.loads(render_openapi())
    assert "/v1/health" in spec["paths"]
    assert "ErrorResponse" in spec["components"]["schemas"]


def test_openapi_client_schema_in_sync() -> None:
    committed = OPENAPI_PATH.read_text(encoding="utf-8")
    assert committed == render_openapi(), "run `make gen-api`"
