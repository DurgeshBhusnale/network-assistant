import httpx
import pytest
from fastapi import FastAPI

from app.core.errors import AppError, ErrorCode


@pytest.fixture
def app_with_routes(app: FastAPI) -> FastAPI:
    @app.get("/test/app-error")
    async def app_error() -> None:
        raise AppError(ErrorCode.CONFLICT, "Already exists", status_code=409)

    @app.get("/test/validated")
    async def validated(limit: int) -> dict[str, int]:
        return {"limit": limit}

    @app.get("/test/crash")
    async def crash() -> None:
        raise RuntimeError("secret detail +91 98765 43210")

    return app


def _assert_envelope(response: httpx.Response, status: int, code: str) -> dict[str, str]:
    assert response.status_code == status
    body = response.json()
    assert set(body) == {"error"}
    assert set(body["error"]) == {"code", "message"}
    assert body["error"]["code"] == code
    assert isinstance(body["error"]["message"], str) and body["error"]["message"]
    error: dict[str, str] = body["error"]
    return error


async def test_error_envelope_shape(app_with_routes: FastAPI, client: httpx.AsyncClient) -> None:
    error = _assert_envelope(await client.get("/test/app-error"), 409, "CONFLICT")
    assert error["message"] == "Already exists"


async def test_unknown_route_uses_envelope(client: httpx.AsyncClient) -> None:
    _assert_envelope(await client.get("/v1/nope"), 404, "NOT_FOUND")


async def test_wrong_method_uses_envelope(client: httpx.AsyncClient) -> None:
    _assert_envelope(await client.post("/v1/health"), 405, "METHOD_NOT_ALLOWED")


async def test_validation_error_names_fields_without_echoing_input(
    app_with_routes: FastAPI, client: httpx.AsyncClient
) -> None:
    response = await client.get("/test/validated", params={"limit": "rohan@example.com"})

    error = _assert_envelope(response, 422, "VALIDATION_ERROR")
    assert "query.limit" in error["message"]
    assert "rohan@example.com" not in response.text


async def test_unhandled_error_hides_details(
    app_with_routes: FastAPI, client: httpx.AsyncClient
) -> None:
    response = await client.get("/test/crash")

    _assert_envelope(response, 500, "INTERNAL_ERROR")
    assert "secret detail" not in response.text
    assert "98765" not in response.text
