"""Regression R6 (RLS isolation on every user-owned table) and R10 (no PII in logs)."""

import hashlib
import hmac
import io
import json
import logging
import uuid

import httpx
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.logging import build_handler
from app.services.privacy import EXPORT_TABLES
from tests.integration.api import WEBHOOK_SECRET, User, ok
from tests.integration.conftest import MakeUser, act_as

PHONE = "+91 98765 12345"
EMAIL = "kavya.rao.private@example.org"
NOTE = "Kavya is quietly interviewing at Swiggy"
CAPTURE = "Met Meera Iyer at a meetup, she runs hiring at CRED"


async def _touch_every_table(u: User, engine: AsyncEngine) -> None:
    """Exercise the API so the user owns rows in (nearly) every table."""
    await u.onboard()
    kavya = await u.contact("Kavya Rao", phone=PHONE, email=EMAIL, company="Zoho")
    ok(await u.post(f"/v1/contacts/{kavya['id']}/memories", {"text": NOTE}), 201)
    draft = ok(await u.post(f"/v1/contacts/{kavya['id']}/draft", {"stage": "warm_up"}), 201)
    ok(await u.post(f"/v1/drafts/{draft['id']}/send", {"channel": "whatsapp"}))
    sent = {
        "contact_id": kavya["id"],
        "type": "sent",
        "draft_id": draft["id"],
        "channel": "whatsapp",
    }
    ok(await u.post("/v1/interactions", sent), 201)
    await u.contact("Arjun Mehta", company="Razorpay")  # not yet messaged: lands on Today
    assert ok(await u.get("/v1/today"))["items"]
    ok(await u.put("/v1/style/samples", {"samples": ["Hey! Long time, how have you been?"]}))
    ok(await u.post("/v1/captures", {"text": CAPTURE}), 201)
    ok(
        await u.post(
            "/v1/imports/picker", {"contacts": [{"name": ["Ravi"], "tel": ["+919812300000"]}]}
        ),
        201,
    )
    order = ok(await u.post("/v1/billing/orders", {"product": "sprint"}), 201)
    ok(await u.post(f"/v1/billing/dev/complete/{order['order_id']}"))
    sub = {"endpoint": f"https://push.example/{uuid.uuid4()}", "keys": {"p256dh": "k", "auth": "a"}}
    ok(await u.post("/v1/push/subscribe", sub), 204)
    async with engine.begin() as conn:
        await conn.execute(
            text(
                "insert into wa_messages (user_id, direction, kind, wa_message_id) "
                "values (:u, 'in', 'text', :m)"
            ),
            {"u": u.id, "m": f"wamid.rls.{uuid.uuid4().hex}"},
        )


async def test_rls_isolates_every_user_owned_table(
    users: MakeUser, api_engine: AsyncEngine
) -> None:
    a, b = await users(), await users()
    await _touch_every_table(a, api_engine)
    ok(await b.get("/v1/me"))

    async with api_engine.connect() as conn:
        owned = {
            t: (
                await conn.execute(
                    text(f"select count(*) from public.{t} where user_id = :u"),  # noqa: S608
                    {"u": a.id},
                )
            ).scalar_one()
            for t in EXPORT_TABLES
        }
    # The flow above must really have populated the tables this test protects.
    empty = {t for t, n in owned.items() if n == 0}
    assert empty <= {"triggers"}, f"not exercised: {sorted(empty)}"

    async with api_engine.connect() as conn:
        tx = await conn.begin()
        try:
            await act_as(conn, b.id)
            for table in EXPORT_TABLES:
                seen = await conn.execute(
                    text(f"select count(*) from public.{table} where user_id = :u"),  # noqa: S608
                    {"u": a.id},
                )
                assert seen.scalar_one() == 0, f"{table}: B can read A's rows"
                await conn.execute(text("savepoint probe"))
                try:
                    changed = await conn.execute(
                        text(f"update public.{table} set user_id = user_id where user_id = :u"),  # noqa: S608
                        {"u": a.id},
                    )
                    assert changed.rowcount == 0, f"{table}: B can update A's rows"
                except AssertionError:
                    raise
                except Exception:  # noqa: S110 - no update grant at all is also isolation
                    pass
                await conn.execute(text("rollback to savepoint probe"))
        finally:
            await tx.rollback()


async def test_no_pii_in_logs_across_core_flows(
    users: MakeUser, api_engine: AsyncEngine, anon: httpx.AsyncClient, api_app: FastAPI
) -> None:
    stream = io.StringIO()
    handler = build_handler(stream)
    root = logging.getLogger()
    level = root.level
    root.addHandler(handler)
    root.setLevel(logging.DEBUG)
    try:
        u = await users()
        await _touch_every_table(u, api_engine)
        ok(await u.get("/v1/contacts", params={"q": "Kavya"}))
        dup = await u.post("/v1/contacts", {"full_name": "Kavya R", "phone": PHONE})
        assert dup.status_code == 409
        bad = await u.post("/v1/contacts", {"full_name": "", "email": EMAIL})
        assert bad.status_code == 422
        raw = json.dumps(
            {
                "object": "whatsapp_business_account",
                "entry": [
                    {
                        "changes": [
                            {
                                "field": "messages",
                                "value": {
                                    "messages": [
                                        {
                                            "from": "919876512345",
                                            "id": f"wamid.logs.{uuid.uuid4().hex}",
                                            "timestamp": "1",
                                            "type": "text",
                                            "text": {"body": NOTE},
                                        }
                                    ]
                                },
                            }
                        ]
                    }
                ],
            }
        ).encode()
        signature = "sha256=" + hmac.new(WEBHOOK_SECRET.encode(), raw, hashlib.sha256).hexdigest()
        res = await anon.post(
            "/v1/webhooks/whatsapp",
            content=raw,
            headers={"content-type": "application/json", "x-hub-signature-256": signature},
        )
        assert res.status_code == 200
    finally:
        root.removeHandler(handler)
        root.setLevel(level)

    logs = stream.getvalue()
    assert logs, "expected some log output"
    for secret in (
        PHONE,
        "9876512345",
        EMAIL,
        u.email,
        NOTE,
        CAPTURE,
        "Meera Iyer",
        "quietly interviewing",
    ):
        assert secret not in logs, f"leaked into logs: {secret!r}"
