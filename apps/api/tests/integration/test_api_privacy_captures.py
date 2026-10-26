"""Captures, data rights, admin metrics and retention (FR-MEM-2/3, FR-PRIV-2/3, FR-AN-2)."""

import io
import json
import uuid
import zipfile
from datetime import UTC, datetime
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.storage import Storage
from app.services.captures import process_capture
from app.services.privacy import EXPORT_TABLES, apply_retention
from tests.integration.api import error_code, ok
from tests.integration.conftest import MakeUser


class _HeldQueue:
    """Accepts jobs and never runs them, so the test drives the worker step itself."""

    async def enqueue_job(self, *_args: Any) -> None:
        return None


async def test_text_capture_to_confirmed_people(users: MakeUser, api_app: FastAPI) -> None:
    u = await users()
    await u.onboard()
    api_app.state.queue = _HeldQueue()
    try:
        capture = ok(
            await u.post("/v1/captures", {"text": "Met Priya Nair, PM at Zoho, at eChai"}), 201
        )
    finally:
        api_app.state.queue = None
    assert capture["status"] == "queued"
    early = await u.post(
        f"/v1/captures/{capture['id']}/confirm", {"decisions": [{"key": "p0", "action": "new"}]}
    )
    assert early.status_code == 409 and error_code(early) == "CAPTURE_NOT_READY"

    await process_capture(
        api_app.state.db_engine,
        api_app.state.ai_router,
        Storage(api_app.state.settings),
        uuid.UUID(capture["id"]),
    )
    ready = ok(await u.get(f"/v1/captures/{capture['id']}"))
    assert ready["status"] == "ready"
    (person,) = ready["people"]
    assert (person["full_name"], person["company"]) == ("Priya Nair", "Zoho")

    today = datetime.now(ZoneInfo("Asia/Kolkata")).date().isoformat()
    decision = {"key": "p0", "action": "new", "follow_up_date": today}
    result = ok(await u.post(f"/v1/captures/{capture['id']}/confirm", {"decisions": [decision]}))
    assert (result["created"], result["merged"], result["follow_ups"]) == (1, 0, 1)
    assert result["memories"] >= 2  # where met + fact + commitment
    (cid,) = result["contact_ids"]
    memories = [m["text"] for m in ok(await u.get(f"/v1/contacts/{cid}"))["memories"]]
    assert "Met at eChai" in memories
    # Rule 7: the capture text is cleared once confirmed.
    assert ok(await u.get(f"/v1/captures/{capture['id']}"))["transcript"] is None
    # R4: the follow-up shows up on its date.
    today_items = ok(await u.get("/v1/today"))["items"]
    assert cid in {i["contact"]["id"] for i in today_items}


async def test_captures_are_private(users: MakeUser) -> None:
    a, b = await users(), await users()
    await a.onboard()
    await b.onboard()
    capture = ok(await a.post("/v1/captures", {"text": "Met someone"}), 201)
    probes = [
        await b.get(f"/v1/captures/{capture['id']}"),
        await b.post(
            f"/v1/captures/{capture['id']}/confirm", {"decisions": [{"key": "p0", "action": "new"}]}
        ),
        await b.post(f"/v1/captures/{capture['id']}/discard"),
    ]
    assert [p.status_code for p in probes] == [404, 404, 404]
    ok(await a.post(f"/v1/captures/{capture['id']}/discard"), 204)


async def test_export_has_every_table_and_only_my_rows(users: MakeUser) -> None:
    a, b = await users(), await users()
    await a.onboard()
    await b.onboard()
    await a.contact("Priya Nair", phone="+919876543210", company="Zoho")
    await b.contact("Bob Secret", phone="+919876500001")
    res = await a.post("/v1/privacy/export")
    assert res.status_code == 200
    assert res.headers["content-type"] == "application/zip"
    assert res.headers["cache-control"] == "no-store"
    zf = zipfile.ZipFile(io.BytesIO(res.content))
    names = set(zf.namelist())
    assert {f"{t}.json" for t in EXPORT_TABLES} <= names
    assert {"contacts.csv", "README.txt"} <= names
    contacts = json.loads(zf.read("contacts.json"))
    assert [c["full_name"] for c in contacts] == ["Priya Nair"]
    everything = b"".join(zf.read(n) for n in names)
    assert b"Bob Secret" not in everything
    assert str(b.id).encode() not in everything
    assert zf.read("contacts.csv").decode().splitlines()[1].startswith("Priya Nair,+919876543210")
    profile = json.loads(zf.read("profiles.json"))
    assert [p["user_id"] for p in profile] == [str(a.id)]


async def test_delete_account_removes_every_row(users: MakeUser, api_engine: AsyncEngine) -> None:
    a, b = await users(), await users()
    await a.onboard()
    await b.onboard()
    priya = await a.contact("Priya Nair", phone="+919876543210", company="Zoho")
    ok(await a.post(f"/v1/contacts/{priya['id']}/memories", {"text": "Met at eChai"}), 201)
    ok(await a.post(f"/v1/contacts/{priya['id']}/draft", {"stage": "warm_up"}), 201)
    ok(await a.get("/v1/today"))
    order = ok(await a.post("/v1/billing/orders", {"product": "sprint"}), 201)
    ok(await a.post(f"/v1/billing/dev/complete/{order['order_id']}"))
    await b.contact("Bob Keeps", phone="+919876500001")

    wrong = await a.post("/v1/privacy/delete-account", {"confirm": "delete me"})
    assert wrong.status_code == 422
    assert (await a.post("/v1/privacy/delete-account", {"confirm": "DELETE"})).status_code == 202

    leftovers: dict[str, int] = {}
    async with api_engine.connect() as conn:
        for table in EXPORT_TABLES:
            n = (
                await conn.execute(
                    text(f"select count(*) from public.{table} where user_id = :u"),  # noqa: S608
                    {"u": a.id},
                )
            ).scalar_one()
            if n:
                leftovers[table] = n
        auth_rows = await conn.execute(
            text("select count(*) from auth.users where id = :u"), {"u": a.id}
        )
        payment = await conn.execute(
            text("select status, user_id from payments where provider_order_id = :o"),
            {"o": order["order_id"]},
        )
        audit = await conn.execute(
            text(
                "select count(*) from audit_log where action = 'delete_account' and user_ref = :r"
            ),
            {"r": str(a.id)},
        )
    assert leftovers == {}
    assert auth_rows.scalar_one() == 0
    assert tuple(payment.one()) == ("paid", None)  # kept for tax, without the user
    assert audit.scalar_one() == 0  # the audit entry holds only a hash
    assert (await a.get("/v1/me")).status_code == 401
    assert [c["full_name"] for c in ok(await b.get("/v1/contacts"))["items"]] == ["Bob Keeps"]
    async with api_engine.begin() as conn:
        await conn.execute(
            text("delete from payments where provider_order_id = :o"), {"o": order["order_id"]}
        )


async def test_admin_metrics_are_owner_only(users: MakeUser, api_app: FastAPI) -> None:
    owner, other = await users(), await users()
    ok(await owner.get("/v1/me"))
    ok(await other.get("/v1/me"))
    denied = await other.get("/v1/admin/metrics")
    assert denied.status_code == 403 and error_code(denied) == "FORBIDDEN"
    settings = api_app.state.settings
    api_app.state.settings = settings.model_copy(update={"admin_user_ids": f" {owner.id} ,x"})
    try:
        metrics: dict[str, Any] = ok(await owner.get("/v1/admin/metrics"))
        assert (await other.get("/v1/admin/metrics")).status_code == 403
    finally:
        api_app.state.settings = settings
    assert metrics["funnel"]["signups"] >= 2
    assert set(metrics) >= {"conversion_pct", "activation_pct", "ai_cost_per_active_user_30d_inr"}
    raw = json.dumps(metrics)
    assert "@" not in raw and str(other.id) not in raw  # aggregates only


async def test_retention_purges_only_what_is_old_enough(
    users: MakeUser, api_engine: AsyncEngine
) -> None:
    u = await users()
    await u.onboard()
    old_gone = await u.contact("Old Deleted", phone="+919000000011")
    recent_gone = await u.contact("Recent Deleted", phone="+919000000012")
    draft_contact = await u.contact("Draft Person", phone="+919000000013")
    old_draft = ok(
        await u.post(f"/v1/contacts/{draft_contact['id']}/draft", {"stage": "warm_up"}), 201
    )
    new_draft = ok(
        await u.post(f"/v1/contacts/{draft_contact['id']}/draft", {"stage": "warm_up"}), 201
    )
    wa_old, wa_new = f"wamid.ret-old.{uuid.uuid4().hex}", f"wamid.ret-new.{uuid.uuid4().hex}"
    async with api_engine.begin() as conn:
        for cid, days in ((old_gone["id"], 31), (recent_gone["id"], 29)):
            await conn.execute(
                text(
                    "update contacts set deleted_at = now() - make_interval(days => :d) "
                    "where id = :id"
                ),
                {"d": days, "id": cid},
            )
        await conn.execute(
            text("update drafts set created_at = now() - interval '181 days' where id = :id"),
            {"id": old_draft["id"]},
        )
        for mid, days in ((wa_old, 91), (wa_new, 89)):
            await conn.execute(
                text(
                    "insert into wa_messages (user_id, direction, kind, wa_message_id, created_at) "
                    "values (:u, 'in', 'text', :m, now() - make_interval(days => :d))"
                ),
                {"u": u.id, "m": mid, "d": days},
            )
        await conn.execute(
            text(
                "insert into events (user_id, name, props, occurred_at) values "
                "(:u, 'retention_old', '{}', now() - interval '400 days'), "
                "(:u, 'retention_new', '{}', now() - interval '390 days')"
            ),
            {"u": u.id},
        )

    counts = await apply_retention(api_engine, datetime.now(UTC))
    assert counts["contacts_purged"] >= 1 and counts["draft_texts_cleared"] >= 1

    async with api_engine.connect() as conn:
        contacts = {
            r[0]
            for r in await conn.execute(
                text("select full_name from contacts where user_id = :u"), {"u": u.id}
            )
        }
        drafts = dict(
            (str(r[0]), r[1])
            for r in await conn.execute(
                text("select id, text from drafts where user_id = :u"), {"u": u.id}
            )
        )
        wa = {
            r[0]
            for r in await conn.execute(
                text("select wa_message_id from wa_messages where user_id = :u"), {"u": u.id}
            )
        }
        events = {
            r[0]
            for r in await conn.execute(
                text("select name from events where user_id = :u and name like 'retention_%'"),
                {"u": u.id},
            )
        }
    assert "Old Deleted" not in contacts and "Recent Deleted" in contacts
    assert drafts[old_draft["id"]] == "" and drafts[new_draft["id"]] != ""
    assert wa == {wa_new}
    assert events == {"retention_new"}
