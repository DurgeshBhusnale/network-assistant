import asyncio

import httpx
import pytest
from fastapi import FastAPI

import app.api.v1.health as health_module
from app.api.v1.health import HealthChecks, get_health_checks


async def _ok() -> None:
    return None


async def _down() -> None:
    raise ConnectionRefusedError("connection refused")


def _use_checks(app: FastAPI, checks: HealthChecks) -> None:
    app.dependency_overrides[get_health_checks] = lambda: checks


async def test_health_ok(app: FastAPI, client: httpx.AsyncClient) -> None:
    _use_checks(app, HealthChecks(db=_ok, redis=_ok))

    response = await client.get("/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "db": "ok", "redis": "ok"}


async def test_health_reports_db_down(app: FastAPI, client: httpx.AsyncClient) -> None:
    _use_checks(app, HealthChecks(db=_down, redis=_ok))

    response = await client.get("/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "down", "redis": "ok"}


async def test_health_reports_redis_down(app: FastAPI, client: httpx.AsyncClient) -> None:
    _use_checks(app, HealthChecks(db=_ok, redis=_down))

    response = await client.get("/v1/health")

    assert response.status_code == 503
    assert response.json() == {"status": "degraded", "db": "ok", "redis": "down"}


async def test_health_treats_a_hanging_check_as_down(
    app: FastAPI, client: httpx.AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    async def _hang() -> None:
        await asyncio.sleep(10)

    monkeypatch.setattr(health_module, "CHECK_TIMEOUT_SECONDS", 0.05)
    _use_checks(app, HealthChecks(db=_hang, redis=_ok))

    response = await client.get("/v1/health")

    assert response.status_code == 503
    assert response.json()["db"] == "down"
