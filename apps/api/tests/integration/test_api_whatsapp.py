"""WhatsApp assistant (FR-WA-*) in dry run: signed webhook, dedupe, linking, commands, STOP/START,
and rule 4 (the bot only ever messages the user's own verified number)."""

import hashlib
import hmac
import json
import uuid
from collections.abc import AsyncIterator
from typing import Any

import httpx
import pytest
from fastapi import FastAPI
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.channels.whatsapp.client import RecipientNotAllowedError, WhatsAppClient
from app.channels.whatsapp.handler import handle_inbound, send_daily_briefs
from app.channels.whatsapp.inbound import Inbound, SharedContact
from app.core.config import Settings
from tests.integration.api import WA_VERIFY_TOKEN, WEBHOOK_SECRET, User, error_code, ok
from tests.integration.conftest import MakeUser

FIXTURES_RUN = uuid.uuid4().hex[:8]


def sign(raw: bytes, secret: str = WEBHOOK_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()


def message(mid: str, sender: str, body: str) -> dict[str, Any]:
    """Meta Cloud API webhook shape for one inbound text message."""
    msg = {
        "from": sender,
        "id": f"wamid.{mid}.{FIXTURES_RUN}",
        "timestamp": "1792900000",
        "type": "text",
        "text": {"body": body},
    }
    value = {"messaging_product": "whatsapp", "messages": [msg]}
    return {
        "object": "whatsapp_business_account",
        "entry": [{"id": "1", "changes": [{"field": "messages", "value": value}]}],
    }


class FakeQueue:
    def __init__(self) -> None:
        self.jobs: list[dict[str, Any]] = []

    async def enqueue_job(self, name: str, *args: Any) -> None:
        if name == "handle_whatsapp":
            self.jobs.append(args[0])


@pytest.fixture
async def queue(api_app: FastAPI) -> AsyncIterator[FakeQueue]:
    fake = FakeQueue()
    api_app.state.queue = fake
    yield fake
    api_app.state.queue = None


class Bot:
    def __init__(self, app: FastAPI, queue: FakeQueue, http: httpx.AsyncClient) -> None:
        self.settings: Settings = app.state.settings
        self.engine: AsyncEngine = app.state.db_engine
        self.router = app.state.ai_router
        self.queue = queue
        self.http = http
        self.wa = WhatsAppClient(self.settings, self.engine)
        assert self.wa.dry_run

    async def hook(self, payload: dict[str, Any], signature: str | None = None) -> int:
        raw = json.dumps(payload).encode()
        res = await self.http.post(
            "/v1/webhooks/whatsapp",
            content=raw,
            headers={
                "content-type": "application/json",
                "x-hub-signature-256": sign(raw) if signature is None else signature,
            },
        )
        return res.status_code

    async def run_jobs(self) -> None:
        jobs, self.queue.jobs = self.queue.jobs, []
        for j in jobs:
            contacts = [SharedContact(**c) for c in j.get("contacts", [])]
            inbound = Inbound(**{**j, "contacts": contacts})
            await handle_inbound(self.engine, self.router, self.wa, self.settings, inbound)

    async def outbound(self, user_id: uuid.UUID) -> list[str]:
        async with self.engine.connect() as conn:
            rows = await conn.execute(
                text(
                    "select kind from wa_messages where user_id = :u and direction = 'out' "
                    "order by created_at"
                ),
                {"u": user_id},
            )
            return [r[0] for r in rows]


@pytest.fixture
def bot(api_app: FastAPI, queue: FakeQueue, anon: httpx.AsyncClient) -> Bot:
    return Bot(api_app, queue, anon)


async def _link(u: User, bot: Bot, phone: str) -> None:
    link = ok(await u.post("/v1/whatsapp/link-code"), 201)
    assert link["wa_url"].startswith("https://wa.me/919800000000?text=")
    assert await bot.hook(message(f"link-{u.id.hex[:6]}", phone, f"start {link['code'].lower()}")) == 200
    await bot.run_jobs()


async def test_webhook_verification_handshake(anon: httpx.AsyncClient) -> None:
    params = {"hub.mode": "subscribe", "hub.verify_token": WA_VERIFY_TOKEN, "hub.challenge": "c-42"}
    res = await anon.get("/v1/webhooks/whatsapp", params=params)
    assert (res.status_code, res.text) == (200, "c-42")
    wrong = await anon.get("/v1/webhooks/whatsapp", params={**params, "hub.verify_token": "nope"})
    assert wrong.status_code == 403


async def test_webhook_rejects_bad_signatures_and_dedupes(bot: Bot) -> None:
    payload = message("sig", "919000000002", "hello")
    assert await bot.hook(payload, signature="sha256=" + "0" * 64) == 401
    assert await bot.hook(payload, signature="") == 401
    raw = json.dumps(payload).encode()
    assert await bot.hook(payload, signature=sign(raw, "attacker-secret")) == 401
    assert bot.queue.jobs == []
    assert await bot.hook(payload) == 200
    assert await bot.hook(payload) == 200  # Meta retries: same message id
    assert len(bot.queue.jobs) == 1
    bot.queue.jobs.clear()


async def test_link_needs_whatsapp_consent(users: MakeUser) -> None:
    u = await users()
    ok(await u.put("/v1/privacy/consents", {"accept_notice": True, "consents": {}}))
    res = await u.post("/v1/whatsapp/link-code")
    assert res.status_code == 403 and error_code(res) == "CONSENT_REQUIRED"


async def test_linking_commands_stop_start_and_the_recipient_guard(
    users: MakeUser, bot: Bot, api_engine: AsyncEngine
) -> None:
    u = await users()
    await u.onboard()
    phone = "9198" + str(uuid.uuid4().int)[:8]
    await _link(u, bot, phone)
    status = ok(await u.get("/v1/whatsapp/status"))
    assert status["linked"] is True and status["opted_out"] is False
    assert status["phone_hint"].endswith(phone[-4:])
    assert await bot.outbound(u.id) == ["text"]  # the "you're linked" confirmation

    await bot.hook(message(f"note-{u.id.hex[:6]}", phone, "Met Kavya Rao, SDE at Zoho, at a meetup"))
    await bot.run_jobs()
    async with api_engine.connect() as conn:
        # Rule 7: the message log has nowhere to put a body or a phone number.
        columns = await conn.execute(
            text(
                "select column_name from information_schema.columns "
                "where table_schema = 'public' and table_name = 'wa_messages'"
            )
        )
        captures = await conn.execute(
            text("select count(*) from captures where user_id = :u and source = 'wa_text'"),
            {"u": u.id},
        )
    assert {c[0] for c in columns} == {
        "id",
        "user_id",
        "direction",
        "kind",
        "template_name",
        "wa_message_id",
        "status",
        "created_at",
    }
    assert captures.scalar_one() == 1

    await bot.hook(message(f"stop-{u.id.hex[:6]}", phone, " Stop "))
    await bot.run_jobs()
    assert ok(await u.get("/v1/whatsapp/status"))["opted_out"] is True
    with pytest.raises(RecipientNotAllowedError):
        await bot.wa.send_text(u.id, "should never go out")
    sent_before = await bot.outbound(u.id)
    await bot.hook(message(f"today-{u.id.hex[:6]}", phone, "TODAY"))
    await bot.run_jobs()
    assert await bot.outbound(u.id) == sent_before  # opted out: nothing sent

    await bot.hook(message(f"start-{u.id.hex[:6]}", phone, "START"))
    await bot.run_jobs()
    assert ok(await u.get("/v1/whatsapp/status"))["opted_out"] is False

    # Withdrawing WhatsApp consent also closes the guard.
    ok(await u.put("/v1/privacy/consents", {"accept_notice": True, "consents": {"whatsapp": False}}))
    with pytest.raises(RecipientNotAllowedError):
        await bot.wa.send_text(u.id, "should never go out")

    ok(await u.delete("/v1/whatsapp/link"), 204)
    assert ok(await u.get("/v1/whatsapp/status"))["linked"] is False


async def test_guard_refuses_users_without_a_verified_number(bot: Bot, users: MakeUser) -> None:
    with pytest.raises(RecipientNotAllowedError):
        await bot.wa.send_text(uuid.uuid4(), "unknown user")
    u = await users()
    await u.onboard()
    with pytest.raises(RecipientNotAllowedError):
        await bot.wa.send_text(u.id, "never linked")


async def test_strangers_get_no_reply(bot: Bot, api_engine: AsyncEngine) -> None:
    count = text("select count(*) from wa_messages where direction = 'out'")
    async with api_engine.connect() as conn:
        before = (await conn.execute(count)).scalar_one()
    stranger = "9199" + str(uuid.uuid4().int)[:8]
    await bot.hook(message(f"stranger-{stranger}", stranger, "hello?"))
    await bot.run_jobs()
    async with api_engine.connect() as conn:
        assert (await conn.execute(count)).scalar_one() == before


async def test_daily_brief_only_for_paid_users_once_a_day(
    users: MakeUser, bot: Bot, api_engine: AsyncEngine
) -> None:
    """Rule 5: we never start a WhatsApp conversation with a free user."""
    u = await users()
    await u.onboard()
    await u.contact("Priya Nair", company="Zoho")
    await _link(u, bot, "9197" + str(uuid.uuid4().int)[:8])
    async with api_engine.begin() as conn:
        await conn.execute(
            text(
                "update profiles set nudge_time = "
                "((now() at time zone timezone) - interval '1 minute')::time where user_id = :u"
            ),
            {"u": u.id},
        )
    before = len(await bot.outbound(u.id))
    await send_daily_briefs(api_engine, bot.wa, bot.settings)
    assert len(await bot.outbound(u.id)) == before  # free: no brief

    async with api_engine.begin() as conn:
        await conn.execute(
            text(
                "insert into entitlements (user_id, product, starts_at, ends_at) "
                "values (:u, 'sprint', now(), now() + interval '60 days')"
            ),
            {"u": u.id},
        )
    await send_daily_briefs(api_engine, bot.wa, bot.settings)
    await send_daily_briefs(api_engine, bot.wa, bot.settings)
    assert len(await bot.outbound(u.id)) == before + 1  # paid: exactly one per day
