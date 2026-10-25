import time
import uuid
from typing import Any

import jwt
import pytest

from app.core.auth import LEEWAY_SECONDS, decode_token
from app.core.config import Settings
from app.core.errors import AppError

SECRET = "test-secret-" + "x" * 32


def _settings() -> Settings:
    return Settings(app_env="test", ai_mode="fake", sentry_dsn=None, supabase_jwt_secret=SECRET)


def _token(**overrides: Any) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
        **overrides,
    }
    return jwt.encode(claims, SECRET, algorithm="HS256")


async def test_accepts_a_fresh_token_issued_slightly_ahead_of_our_clock() -> None:
    # Supabase's clock can be a second or two ahead; a just-issued token must still work.
    token = _token(iat=int(time.time()) + 3)
    claims = await decode_token(token, _settings())
    assert claims["role"] == "authenticated"


@pytest.mark.parametrize(
    ("overrides", "message"),
    [
        ({"exp": int(time.time()) - LEEWAY_SECONDS - 5}, "expired"),
        ({"iat": int(time.time()) + LEEWAY_SECONDS + 60}, "Sign in"),
        ({"aud": "anon"}, "Sign in"),
        ({"role": "anon"}, "Sign in"),
    ],
)
async def test_rejects_bad_tokens(overrides: dict[str, Any], message: str) -> None:
    with pytest.raises(AppError) as exc:
        await decode_token(_token(**overrides), _settings())
    assert exc.value.status_code == 401
    assert message in exc.value.message


async def test_rejects_wrong_signature() -> None:
    token = jwt.encode(
        {"sub": "x", "aud": "authenticated", "role": "authenticated"},
        "another-secret-" + "y" * 32,
        algorithm="HS256",
    )
    with pytest.raises(AppError):
        await decode_token(token, _settings())
