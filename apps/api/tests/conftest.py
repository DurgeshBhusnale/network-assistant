import json
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

import httpx
import pytest
from fastapi import FastAPI

os.environ["AI_MODE"] = "fake"
os.environ.setdefault("APP_ENV", "test")

from app.core.config import REPO_ROOT, Settings
from app.main import create_app

FIXTURES = Path(__file__).parent / "fixtures"


def load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture
def settings() -> Settings:
    return Settings(app_env="test", ai_mode="fake", sentry_dsn=None)


@pytest.fixture
def app(settings: Settings) -> FastAPI:
    return create_app(settings)


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=app, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.fixture
def career_sprint_config() -> dict[str, Any]:
    data: dict[str, Any] = load_json(REPO_ROOT / "packs" / "career_sprint.json")
    return data


@pytest.fixture
def freelance_test_config() -> dict[str, Any]:
    data: dict[str, Any] = load_json(FIXTURES / "packs" / "freelance_test.json")
    return data
