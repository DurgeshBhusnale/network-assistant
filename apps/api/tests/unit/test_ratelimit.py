import uuid
from types import SimpleNamespace
from typing import Any

import pytest

from app.core.auth import AuthUser
from app.core.config import Settings
from app.core.errors import AppError
from app.core.ratelimit import general_limit


class FakeRedis:
    def __init__(self) -> None:
        self.counts: dict[str, int] = {}

    async def incr(self, key: str) -> int:
        self.counts[key] = self.counts.get(key, 0) + 1
        return self.counts[key]

    async def expire(self, key: str, seconds: int) -> None:
        return None


def _request(settings: Settings, redis: FakeRedis) -> Any:
    return SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(settings=settings, redis=redis))
    )


@pytest.mark.parametrize(("per_minute", "allowed"), [(60, 60), (5, 5)])
async def test_general_limit_comes_from_settings(per_minute: int, allowed: int) -> None:
    settings = Settings(app_env="test", ai_mode="fake", rate_limit_general_per_minute=per_minute)
    request, user = (
        _request(settings, FakeRedis()),
        AuthUser(id=uuid.uuid4(), email=None, claims={}),
    )
    for _ in range(allowed):
        await general_limit(request, user)
    with pytest.raises(AppError) as exc:
        await general_limit(request, user)
    assert exc.value.status_code == 429


def test_default_matches_the_tech_spec() -> None:
    assert Settings(app_env="test", ai_mode="fake").rate_limit_general_per_minute == 60
