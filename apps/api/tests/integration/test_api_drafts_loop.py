"""Drafts and the daily loop (FR-DRAFT-*, FR-TODAY-*, FR-SEND-*, FR-TRACK-*), with fake AI.

The user sends, never the app: /send only builds a wa.me link or copy text, counted against the
daily cap once per draft; nothing is "sent" until the user marks it.
"""

import asyncio
from typing import Any

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from tests.integration.api import User, error_code, ok
from tests.integration.conftest import MakeUser


async def _person_with_draft(u: User, **contact: Any) -> tuple[dict[str, Any], dict[str, Any]]:
    person = await u.contact("Priya Nair", company="Zoho", **contact)
    ok(await u.post(f"/v1/contacts/{person['id']}/memories", {"text": "Met at eChai Pune"}), 201)
    draft = ok(await u.post(f"/v1/contacts/{person['id']}/draft", {"stage": "warm_up"}), 201)
    return person, draft


async def test_draft_edit_send_and_mark_sent(users: MakeUser) -> None:
    u = await users()
    await u.onboard()
    person, draft = await _person_with_draft(u, phone="+919876543210")
    assert draft["stage"] == "warm_up" and draft["text"].strip()
    assert draft["drafts_left_this_month"] == 2  # free plan: 3 per month

    edited = ok(await u.patch(f"/v1/drafts/{draft['id']}", {"final_text": "Hi Priya! How's Zoho?"}))
    assert edited["final_text"] == "Hi Priya! How's Zoho?"

    send = ok(await u.post(f"/v1/drafts/{draft['id']}/send", {"channel": "whatsapp"}))
    assert send["open_url"].startswith("https://wa.me/919876543210?text=Hi%20Priya")
    assert send["copy_text"] == "Hi Priya! How's Zoho?"
    assert send["sends_left_today"] == 19
    # Opening the same draft again doesn't use up another send.
    again = ok(await u.post(f"/v1/drafts/{draft['id']}/send", {"channel": "whatsapp"}))
    assert again["sends_left_today"] == 19
    assert ok(await u.get(f"/v1/drafts/{draft['id']}"))["sent_at"] is None  # not sent yet

    body = {
        "contact_id": person["id"],
        "type": "sent",
        "draft_id": draft["id"],
        "channel": "whatsapp",
    }
    ok(await u.post("/v1/interactions", body), 201)
    assert ok(await u.get(f"/v1/drafts/{draft['id']}"))["sent_at"] is not None
    dup = await u.post("/v1/interactions", body)
    assert dup.status_code == 409

    history = ok(await u.get(f"/v1/contacts/{person['id']}"))["history"]
    assert [h["kind"] for h in history if h["kind"] != "added"] == ["sent"]


async def test_send_without_phone_and_via_linkedin(users: MakeUser) -> None:
    u = await users()
    await u.onboard()
    _, draft = await _person_with_draft(u, linkedin_url="https://www.linkedin.com/in/priya-it")
    no_phone = await u.post(f"/v1/drafts/{draft['id']}/send", {"channel": "whatsapp"})
    assert no_phone.status_code == 422 and error_code(no_phone) == "NO_PHONE"
    linkedin = ok(await u.post(f"/v1/drafts/{draft['id']}/send", {"channel": "linkedin"}))
    assert linkedin["open_url"] == "https://www.linkedin.com/in/priya-it"


async def test_daily_send_cap(users: MakeUser, api_engine: AsyncEngine) -> None:
    """Rule 3: no mass messaging. The 21st message opened today is refused."""
    u = await users()
    await u.onboard()
    _, draft = await _person_with_draft(u, phone="+919876543210")
    async with api_engine.begin() as conn:
        await conn.execute(
            text(
                "insert into drafts (user_id, contact_id, stage, language, provider, model, "
                "prompt_version, text, send_opened_at) "
                "select user_id, contact_id, stage, language, provider, model, prompt_version, "
                "text, now() from drafts, generate_series(1, 20) where id = :id"
            ),
            {"id": draft["id"]},
        )
    capped = await u.post(f"/v1/drafts/{draft['id']}/send", {"channel": "whatsapp"})
    assert capped.status_code == 429
    assert error_code(capped) == "SEND_CAP_REACHED"


async def test_free_plan_limits(users: MakeUser) -> None:
    """Rule 5: free costs almost nothing. 3 drafts a month, 3 rewrites per draft."""
    u = await users()
    await u.onboard()
    person = await u.contact("Priya Nair", company="Zoho")
    drafts = [
        ok(await u.post(f"/v1/contacts/{person['id']}/draft", {"stage": "warm_up"}), 201)
        for _ in range(3)
    ]
    assert [d["drafts_left_this_month"] for d in drafts] == [2, 1, 0]
    fourth = await u.post(f"/v1/contacts/{person['id']}/draft", {"stage": "warm_up"})
    assert fourth.status_code == 402 and error_code(fourth) == "FREE_LIMIT_REACHED"

    first = drafts[0]["id"]
    left = [
        ok(await u.post(f"/v1/drafts/{first}/regenerate", {"tone": "shorter"}))[
            "regenerations_left"
        ]
        for _ in range(3)
    ]
    assert left == [2, 1, 0]
    more = await u.post(f"/v1/drafts/{first}/regenerate", {"tone": "warmer"})
    assert more.status_code == 402 and error_code(more) == "FREE_REGEN_LIMIT_REACHED"

    # R5: upgrading unlocks drafting straight away.
    order = ok(await u.post("/v1/billing/orders", {"product": "sprint"}), 201)
    ok(await u.post(f"/v1/billing/dev/complete/{order['order_id']}"))
    unlocked = ok(await u.post(f"/v1/contacts/{person['id']}/draft", {"stage": "warm_up"}), 201)
    assert unlocked["drafts_left_this_month"] is None
    ok(await u.post(f"/v1/drafts/{first}/regenerate", {"tone": "warmer"}))


async def test_draft_needs_a_goal_and_a_known_stage(users: MakeUser) -> None:
    u = await users()
    ok(await u.put("/v1/privacy/consents", {"accept_notice": True, "consents": {}}))
    person = await u.contact("Priya Nair")
    no_goal = await u.post(f"/v1/contacts/{person['id']}/draft", {"stage": "warm_up"})
    assert no_goal.status_code == 409 and error_code(no_goal) == "NO_ACTIVE_GOAL"
    await u.onboard()
    bad = await u.post(f"/v1/contacts/{person['id']}/draft", {"stage": "spam_everyone"})
    assert bad.status_code == 422


async def test_today_list_snooze_dismiss_and_draft(users: MakeUser) -> None:
    u = await users()
    await u.onboard()
    for name, company in [
        ("Priya Nair", "Zoho"),
        ("Arjun Mehta", "Razorpay"),
        ("Ravi Kumar", "TCS"),
    ]:
        await u.contact(name, company=company, phone=None)
    today = ok(await u.get("/v1/today"))
    assert today["goal"]["day_number"] == 1
    items = today["items"]
    assert {i["contact"]["full_name"] for i in items} >= {"Priya Nair", "Arjun Mehta"}
    assert all(i["stage"] == "warm_up" for i in items)  # cold contacts: reconnect, no ask
    assert ok(await u.get("/v1/today"))["items"] == items  # stable within the day

    first, second = items[0], items[1]
    draft = ok(await u.post(f"/v1/suggestions/{first['id']}/draft", {}), 201)
    assert draft["contact_id"] == first["contact"]["id"]
    ok(await u.post(f"/v1/suggestions/{second['id']}/snooze", {"days": 7}), 204)
    left = {i["id"] for i in ok(await u.get("/v1/today"))["items"]}
    assert second["id"] not in left

    bad_snooze = await u.post(f"/v1/suggestions/{first['id']}/snooze", {"days": 3})
    assert bad_snooze.status_code == 422


async def test_reply_outcome_thanks_and_progress(users: MakeUser) -> None:
    u = await users()
    await u.onboard()
    person, draft = await _person_with_draft(u, phone="+919876543210")
    pid = person["id"]
    ok(
        await u.post(
            "/v1/interactions", {"contact_id": pid, "type": "sent", "draft_id": draft["id"]}
        ),
        201,
    )
    ok(await u.post("/v1/interactions", {"contact_id": pid, "type": "replied"}), 201)
    bad = await u.post(
        "/v1/interactions", {"contact_id": pid, "type": "outcome", "outcome": "hired!"}
    )
    assert bad.status_code == 422
    won = ok(
        await u.post(
            "/v1/interactions", {"contact_id": pid, "type": "outcome", "outcome": "referred"}
        ),
        201,
    )
    assert won["thank_suggestion"] is True
    progress = ok(await u.get("/v1/progress"))
    assert progress["warm_replies_this_week"] == 1
    funnel = {step["key"]: step["count"] for step in progress["funnel"]}
    assert funnel["referred"] == 1
    thank = [i for i in ok(await u.get("/v1/today"))["items"] if i["contact"]["id"] == pid]
    assert [i["stage"] for i in thank] == ["thank"]


async def test_reply_check_in_window(users: MakeUser, api_engine: AsyncEngine) -> None:
    """R3: people messaged 2-5 days ago come back as 'Did they reply?'."""
    u = await users()
    await u.onboard()
    person, draft = await _person_with_draft(u, phone="+919876543210")
    sent = {"contact_id": person["id"], "type": "sent", "draft_id": draft["id"]}
    ok(await u.post("/v1/interactions", sent), 201)
    assert ok(await u.get("/v1/replies/pending"))["items"] == []  # too soon
    async with api_engine.begin() as conn:
        await conn.execute(
            text(
                "update interactions set occurred_at = now() - interval '3 days' "
                "where user_id = :u and type = 'sent'"
            ),
            {"u": u.id},
        )
    pending = ok(await u.get("/v1/replies/pending"))
    assert [(i["contact"]["id"], i["days_ago"]) for i in pending["items"]] == [(person["id"], 3)]
    assert "referred" in {o["id"] for o in pending["outcomes"]}


async def test_drafts_and_suggestions_are_invisible_to_other_users(users: MakeUser) -> None:
    a, b = await users(), await users()
    await a.onboard()
    await b.onboard()
    person, draft = await _person_with_draft(a, phone="+919876543210")
    suggestion = ok(await a.get("/v1/today"))["items"][0]
    did, sid = draft["id"], suggestion["id"]
    probes = [
        await b.get(f"/v1/drafts/{did}"),
        await b.patch(f"/v1/drafts/{did}", {"final_text": "hacked"}),
        await b.post(f"/v1/drafts/{did}/regenerate", {}),
        await b.post(f"/v1/drafts/{did}/send", {"channel": "whatsapp"}),
        await b.post("/v1/interactions", {"contact_id": person["id"], "type": "replied"}),
        await b.post(f"/v1/suggestions/{sid}/draft", {}),
        await b.post(f"/v1/suggestions/{sid}/snooze", {"days": 7}),
        await b.post(f"/v1/suggestions/{sid}/dismiss"),
    ]
    assert [p.status_code for p in probes] == [404] * len(probes)
    assert ok(await b.get("/v1/today"))["items"] == []
    assert ok(await b.get("/v1/replies/pending"))["items"] == []
    assert ok(await a.get(f"/v1/drafts/{did}"))["final_text"] is None


async def test_concurrent_edits_of_one_draft_both_finish(users: MakeUser) -> None:
    """The draft screen saves on blur and again just before sending: two PATCHes at once."""
    u = await users()
    await u.onboard()
    _, draft = await _person_with_draft(u, phone="+919876543210")
    url = f"/v1/drafts/{draft['id']}"
    first, second = await asyncio.wait_for(
        asyncio.gather(
            u.patch(url, {"final_text": "Hi Priya, version one"}),
            u.patch(url, {"final_text": "Hi Priya, version two"}),
        ),
        timeout=30,
    )
    assert (first.status_code, second.status_code) == (200, 200)
