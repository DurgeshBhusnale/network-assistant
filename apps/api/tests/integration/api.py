"""Helpers for API integration tests: the real app against the dev project, throwaway users.

Users are inserted straight into auth.users and signed in with tokens minted from a test-only
HS256 secret that only the in-process app trusts. The `users` fixture deletes them afterwards;
every user-owned row goes with them (FK cascade), plus the few rows that outlive a user.
"""

import time
import uuid
from dataclasses import dataclass
from typing import Any

import httpx
import jwt
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

TEST_JWT_SECRET = "integration-test-secret-" + "z" * 32
WEBHOOK_SECRET = "integration-webhook-secret"
WA_VERIFY_TOKEN = "integration-verify-token"
UNSUBSCRIBE_SECRET = "integration-unsubscribe-secret"

ALL_CONSENTS = {"contacts": True, "voice": True, "whatsapp": True, "analytics": True}


def mint_token(user_id: uuid.UUID, email: str) -> str:
    now = int(time.time())
    claims = {
        "sub": str(user_id),
        "email": email,
        "aud": "authenticated",
        "role": "authenticated",
        "iat": now,
        "exp": now + 3600,
    }
    return jwt.encode(claims, TEST_JWT_SECRET, algorithm="HS256")


def ok(res: httpx.Response, status: int = 200) -> Any:
    assert res.status_code == status, f"{res.request.method} {res.request.url}: {res.text}"
    return res.json() if res.content else None


def error_code(res: httpx.Response) -> str:
    code: str = res.json()["error"]["code"]
    return code


@dataclass
class User:
    id: uuid.UUID
    email: str
    http: httpx.AsyncClient

    async def get(self, url: str, **kw: Any) -> httpx.Response:
        return await self.http.get(url, **kw)

    async def post(self, url: str, json: Any = None, **kw: Any) -> httpx.Response:
        return await self.http.post(url, json=json, **kw)

    async def put(self, url: str, json: Any = None) -> httpx.Response:
        return await self.http.put(url, json=json)

    async def patch(self, url: str, json: Any = None) -> httpx.Response:
        return await self.http.patch(url, json=json)

    async def delete(self, url: str) -> httpx.Response:
        return await self.http.delete(url)

    async def onboard(self, companies: tuple[str, ...] = ("Zoho", "Razorpay")) -> dict[str, Any]:
        """Notice accepted, every consent granted, an active Career Sprint goal, onboarding done."""
        ok(await self.put("/v1/privacy/consents", {"accept_notice": True, "consents": ALL_CONSENTS}))
        goal: dict[str, Any] = ok(
            await self.post(
                "/v1/goals",
                {
                    "pack_id": "career_sprint",
                    "params": {"role": "Backend Engineer", "companies": list(companies)},
                },
            ),
            201,
        )
        ok(await self.patch("/v1/me", {"onboarding_step": "done", "timezone": "Asia/Kolkata"}))
        return goal

    async def contact(self, name: str, **fields: Any) -> dict[str, Any]:
        created: dict[str, Any] = ok(await self.post("/v1/contacts", {"full_name": name, **fields}), 201)
        return created


async def insert_auth_user(engine: AsyncEngine) -> tuple[uuid.UUID, str]:
    user_id = uuid.uuid4()
    email = f"it-{user_id.hex[:12]}@example.test"
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into auth.users (id, email, aud, role, created_at, updated_at) "
                "values (:id, :email, 'authenticated', 'authenticated', now(), now())"
            ),
            {"id": user_id, "email": email},
        )
    return user_id, email


async def delete_users(engine: AsyncEngine, ids: list[uuid.UUID]) -> None:
    if not ids:
        return
    refs = [str(i) for i in ids]
    async with engine.begin() as conn:
        # Rows that deliberately outlive a user (payments for tax, audit trail) are test data here.
        await conn.execute(text("delete from payments where user_id = any(:ids)"), {"ids": ids})
        await conn.execute(text("delete from wa_messages where user_id = any(:ids)"), {"ids": ids})
        await conn.execute(text("delete from audit_log where user_ref = any(:r)"), {"r": refs})
        await conn.execute(text("delete from auth.users where id = any(:ids)"), {"ids": ids})
