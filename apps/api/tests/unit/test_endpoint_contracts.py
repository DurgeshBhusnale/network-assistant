"""Contract checks that run for every endpoint in the OpenAPI schema (no database needed):
private endpoints refuse anonymous and forged tokens, and bad input gets the 422 envelope."""

import re
import time
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import jwt
import pytest
from sqlalchemy.ext.asyncio import create_async_engine

from app.core.config import Settings
from app.main import create_app

SECRET = "contract-test-secret-" + "x" * 32

# Reachable without a session. Adding to this list is a security decision: say why.
PUBLIC = {
    ("GET", "/v1/health"),  # uptime checks
    ("GET", "/v1/webhooks/whatsapp"),  # Meta verify handshake (verify token)
    ("POST", "/v1/webhooks/whatsapp"),  # Meta events (X-Hub-Signature-256)
    ("POST", "/v1/webhooks/razorpay"),  # Razorpay events (X-Razorpay-Signature)
    ("GET", "/v1/billing/plans"),  # prices on the Upgrade screen
    ("GET", "/v1/push/config"),  # VAPID public key
    ("GET", "/v1/email/unsubscribe"),  # signed one-click link from emails
}


def _settings() -> Settings:
    return Settings(app_env="test", ai_mode="fake", sentry_dsn=None, supabase_jwt_secret=SECRET)


def _url(path: str, value: str | None = None) -> str:
    return re.sub(r"\{[^}]+\}", value or str(uuid.uuid4()), path)


def _token(secret: str = SECRET) -> str:
    now = int(time.time())
    claims = {
        "sub": str(uuid.uuid4()),
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 600,
    }
    return jwt.encode(claims, secret, algorithm="HS256")


def _app() -> Any:
    app = create_app(_settings())
    # Never connected: every request here fails auth or validation before touching the DB.
    app.state.db_engine = create_async_engine("postgresql+asyncpg://none@127.0.0.1:9/none")
    app.state.redis = None
    # Stand-in so AI routes reach input validation (the real router needs app startup).
    app.state.ai_router = object()
    return app


APP = _app()


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    transport = httpx.ASGITransport(app=APP, raise_app_exceptions=False)
    async with httpx.AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


def _operations() -> list[tuple[str, str, dict[str, Any]]]:
    schema = APP.openapi()
    return [
        (method.upper(), path, op)
        for path, ops in schema["paths"].items()
        for method, op in ops.items()
    ]


OPERATIONS = _operations()
PRIVATE = [(m, p, op) for m, p, op in OPERATIONS if (m, p) not in PUBLIC]


def test_public_allowlist_matches_real_routes() -> None:
    assert {(m, p) for m, p, _ in OPERATIONS} >= PUBLIC


@pytest.mark.parametrize(("method", "path", "op"), PRIVATE, ids=[f"{m} {p}" for m, p, _ in PRIVATE])
@pytest.mark.parametrize(
    "authorization",
    [None, "Bearer not-a-jwt", "Basic abc", "forged"],
    ids=["none", "garbage", "wrong-scheme", "forged-signature"],
)
async def test_private_endpoints_refuse_unauthenticated(
    client: httpx.AsyncClient, method: str, path: str, op: dict[str, Any], authorization: str | None
) -> None:
    if authorization == "forged":
        authorization = f"Bearer {_token(secret='attacker-secret-' + 'y' * 32)}"
    headers = {"Authorization": authorization} if authorization else {}
    res = await client.request(method, _url(path), headers=headers)
    assert res.status_code == 401, res.text
    assert res.json()["error"]["code"] == "UNAUTHENTICATED"


WITH_UUID_PARAM = [
    (m, p, op)
    for m, p, op in PRIVATE
    if any(
        prm.get("in") == "path" and prm.get("schema", {}).get("format") == "uuid"
        for prm in op.get("parameters", [])
    )
]


@pytest.mark.parametrize(
    ("method", "path", "op"), WITH_UUID_PARAM, ids=[f"{m} {p}" for m, p, _ in WITH_UUID_PARAM]
)
async def test_malformed_ids_get_validation_envelope(
    client: httpx.AsyncClient, method: str, path: str, op: dict[str, Any]
) -> None:
    res = await client.request(
        method, _url(path, "not-a-uuid"), headers={"Authorization": f"Bearer {_token()}"}
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"


WITH_JSON_BODY = [
    (m, p, op)
    for m, p, op in PRIVATE
    if op.get("requestBody", {}).get("content", {}).get("application/json")
]


@pytest.mark.parametrize(
    ("method", "path", "op"), WITH_JSON_BODY, ids=[f"{m} {p}" for m, p, _ in WITH_JSON_BODY]
)
async def test_wrong_body_type_gets_validation_envelope(
    client: httpx.AsyncClient, method: str, path: str, op: dict[str, Any]
) -> None:
    res = await client.request(
        method,
        _url(path),
        headers={"Authorization": f"Bearer {_token()}"},
        content=b"[1, 2, 3]",
    )
    assert res.status_code == 422, res.text
    assert res.json()["error"]["code"] == "VALIDATION_ERROR"
