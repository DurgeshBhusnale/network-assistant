"""Accounts, goals, notifications and billing (FR-ONB-*, FR-GOAL-*, FR-NOT-*, FR-PAY-*).

Entitlements come only from the signed Razorpay webhook (recorded fixtures, real HMAC check)."""

import hashlib
import hmac
import json
import uuid
from pathlib import Path
from typing import Any

import httpx

from app.services.notifications import unsubscribe_token
from tests.integration.api import WEBHOOK_SECRET, User, error_code, ok
from tests.integration.conftest import MakeUser

FIXTURES = Path(__file__).parent.parent / "fixtures" / "razorpay"


def razorpay_event(name: str, *, order_id: str, payment_id: str, amount: int) -> bytes:
    raw = (FIXTURES / f"{name}.json").read_text(encoding="utf-8")
    filled = (
        raw.replace("{{order_id}}", order_id)
        .replace("{{payment_id}}", payment_id)
        .replace("{{amount}}", str(amount))
    )
    return json.dumps(json.loads(filled)).encode()


async def post_webhook(
    anon: httpx.AsyncClient, raw: bytes, *, event_id: str, secret: str = WEBHOOK_SECRET
) -> int:
    signature = hmac.new(secret.encode(), raw, hashlib.sha256).hexdigest()
    res = await anon.post(
        "/v1/webhooks/razorpay",
        content=raw,
        headers={
            "content-type": "application/json",
            "x-razorpay-signature": signature,
            "x-razorpay-event-id": event_id,
        },
    )
    return res.status_code


# --- accounts and goals ------------------------------------------------------------------


async def test_profile_created_on_first_call_and_validated(users: MakeUser) -> None:
    u = await users()
    me = ok(await u.get("/v1/me"))
    assert me["email"] == u.email
    assert (me["onboarding_step"], me["privacy_notice_accepted"]) == ("goal", False)
    for bad in ({"timezone": "Mars/Olympus"}, {"language": "klingon"}, {"nudge_time": "25:00"}):
        res = await u.patch("/v1/me", bad)
        assert res.status_code == 422, bad
    updated = ok(await u.patch("/v1/me", {"display_name": "Rohan", "timezone": "Asia/Dubai"}))
    assert (updated["display_name"], updated["timezone"]) == ("Rohan", "Asia/Dubai")


async def test_consents_are_opt_in_and_withdrawable(users: MakeUser) -> None:
    u = await users()
    initial = ok(await u.get("/v1/privacy/consents"))
    assert not initial["notice_accepted"]
    assert not any(c["granted"] for c in initial["consents"].values())
    refused = await u.put("/v1/privacy/consents", {"accept_notice": False, "consents": {}})
    assert refused.status_code == 422 and error_code(refused) == "PRIVACY_NOTICE_REQUIRED"

    granted = ok(
        await u.put("/v1/privacy/consents", {"accept_notice": True, "consents": {"voice": True}})
    )
    assert (
        granted["consents"]["voice"]["granted"] and not granted["consents"]["contacts"]["granted"]
    )
    withdrawn = ok(
        await u.put("/v1/privacy/consents", {"accept_notice": True, "consents": {"voice": False}})
    )
    assert not withdrawn["consents"]["voice"]["granted"]
    res = await u.post("/v1/captures/upload-url", {"mime": "audio/webm"})
    assert res.status_code == 403 and error_code(res) == "CONSENT_REQUIRED"


async def test_goal_rules(users: MakeUser) -> None:
    a, b = await users(), await users()
    goal = await a.onboard()
    assert goal["params"]["referrals_target"] == 4  # pack default
    again = await a.post(
        "/v1/goals", {"pack_id": "career_sprint", "params": {"role": "SRE", "companies": ["TCS"]}}
    )
    assert again.status_code == 409 and error_code(again) == "GOAL_ALREADY_ACTIVE"
    bad = await a.patch(f"/v1/goals/{goal['id']}", {"params": {"role": "x", "companies": []}})
    assert bad.status_code == 422
    no_notice = await b.post("/v1/goals", {"pack_id": "career_sprint", "params": {}})
    assert no_notice.status_code == 403
    ok(await b.put("/v1/privacy/consents", {"accept_notice": True, "consents": {}}))
    soon = await b.post("/v1/goals", {"pack_id": "freelance_clients", "params": {}})
    assert soon.status_code == 422 and error_code(soon) == "PACK_NOT_AVAILABLE"

    ok(await a.patch(f"/v1/goals/{goal['id']}", {"status": "paused"}))
    assert ok(await a.get("/v1/goals/active")) is None
    assert ok(await a.get("/v1/goals/current"))["status"] == "paused"
    assert (await b.patch(f"/v1/goals/{goal['id']}", {"status": "done"})).status_code == 404
    assert ok(await a.get("/v1/goals/current"))["status"] == "paused"


# --- notifications -----------------------------------------------------------------------


async def test_push_subscription_and_email_unsubscribe(
    users: MakeUser, anon: httpx.AsyncClient, api_app: Any
) -> None:
    u = await users()
    await u.onboard()
    sub = {
        "endpoint": f"https://fcm.googleapis.com/fcm/send/{uuid.uuid4()}",
        "keys": {"p256dh": "k", "auth": "a"},
    }
    ok(await u.post("/v1/push/subscribe", sub), 204)
    ok(await u.post("/v1/push/subscribe", sub), 204)  # idempotent
    res = await u.http.request("DELETE", "/v1/push/subscribe", json=sub)
    assert res.status_code == 204

    assert ok(await u.get("/v1/me"))["email_digest"] is True
    bad = await anon.get("/v1/email/unsubscribe", params={"u": str(u.id), "t": "forged"})
    assert bad.status_code == 400
    assert ok(await u.get("/v1/me"))["email_digest"] is True
    token = unsubscribe_token(api_app.state.settings, u.id)
    good = await anon.post("/v1/email/unsubscribe", params={"u": str(u.id), "t": token})
    assert good.status_code == 200
    assert ok(await u.get("/v1/me"))["email_digest"] is False


# --- billing -----------------------------------------------------------------------------


async def _order(u: User) -> dict[str, Any]:
    order: dict[str, Any] = ok(await u.post("/v1/billing/orders", {"product": "sprint"}), 201)
    assert order["dev_checkout"] is True and order["order_id"].startswith("order_dev_")
    return order


async def test_plans_and_free_entitlement(users: MakeUser, anon: httpx.AsyncClient) -> None:
    plans = ok(await anon.get("/v1/billing/plans"))
    sprint = next(p for p in plans["products"] if p["product"] == "sprint")
    assert sprint["price_paise"] > 0 and isinstance(sprint["price_paise"], int)
    u = await users()
    ent = ok(await u.get("/v1/billing/entitlement"))
    assert (ent["plan"], ent["free_drafts_left"]) == ("free", 3)
    bad = await u.post("/v1/billing/orders", {"product": "lifetime_vip"})
    assert bad.status_code == 422


async def test_signed_webhook_grants_once_and_refund_ends_it(
    users: MakeUser, anon: httpx.AsyncClient
) -> None:
    u = await users()
    await u.onboard()
    order = await _order(u)
    oid, amount = order["order_id"], order["amount_paise"]
    pid = f"pay_it_{uuid.uuid4().hex[:12]}"
    captured = razorpay_event("payment.captured", order_id=oid, payment_id=pid, amount=amount)

    assert await post_webhook(anon, captured, event_id="evt_1", secret="wrong-secret") == 400
    assert ok(await u.get("/v1/billing/entitlement"))["plan"] == "free"
    unsigned = await anon.post("/v1/webhooks/razorpay", content=captured)
    assert unsigned.status_code == 400

    assert await post_webhook(anon, captured, event_id=f"evt_cap_{pid}") == 200
    ent = ok(await u.get("/v1/billing/entitlement"))
    assert ent["plan"] == "sprint" and ent["days_left"] >= 59
    # Razorpay sends both events and retries: neither extends the plan again.
    paid = razorpay_event("order.paid", order_id=oid, payment_id=pid, amount=amount)
    assert await post_webhook(anon, paid, event_id=f"evt_paid_{pid}") == 200
    assert await post_webhook(anon, captured, event_id=f"evt_cap_{pid}") == 200
    assert ok(await u.get("/v1/billing/entitlement"))["ends_at"] == ent["ends_at"]
    assert ok(await u.get(f"/v1/billing/orders/{oid}"))["status"] == "paid"

    refund = razorpay_event("refund.processed", order_id=oid, payment_id=pid, amount=amount)
    assert await post_webhook(anon, refund, event_id=f"evt_ref_{pid}") == 200
    assert ok(await u.get("/v1/billing/entitlement"))["plan"] == "free"


async def test_second_purchase_extends_instead_of_overlapping(users: MakeUser) -> None:
    u = await users()
    await u.onboard()
    first = await _order(u)
    ok(await u.post(f"/v1/billing/dev/complete/{first['order_id']}"))
    days = ok(await u.get("/v1/billing/entitlement"))["days_left"]
    second = await _order(u)
    ok(await u.post(f"/v1/billing/dev/complete/{second['order_id']}"))
    assert ok(await u.get("/v1/billing/entitlement"))["days_left"] >= days + 59


async def test_orders_are_private(users: MakeUser) -> None:
    a, b = await users(), await users()
    await a.onboard()
    order = await _order(a)
    assert (await b.get(f"/v1/billing/orders/{order['order_id']}")).status_code == 404
    assert (await b.post(f"/v1/billing/dev/complete/{order['order_id']}")).status_code == 404
    assert ok(await b.get("/v1/billing/entitlement"))["plan"] == "free"
    assert ok(await a.get(f"/v1/billing/orders/{order['order_id']}"))["status"] == "created"
