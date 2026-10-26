"""People: contacts, memories, imports (FR-CON-*, FR-MEM-1). Success, validation, isolation."""

import uuid

import pytest

from app.services import contacts as contacts_svc
from tests.integration.api import ok
from tests.integration.conftest import MakeUser

LINKEDIN_CSV = (
    "Notes:\n\n"
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "Kavya,Rao,https://www.linkedin.com/in/kavya-rao-it,,Zoho,SDE,01 Jan 2024\n"
    "Imran,Shaikh,https://www.linkedin.com/in/imran-it,imran@example.com,Swiggy,PM,02 Feb 2024\n"
    ",,https://www.linkedin.com/in/nobody-it,,Acme,,\n"
)


async def test_contact_lifecycle(users: MakeUser) -> None:
    a = await users()
    await a.onboard()
    priya = await a.contact("priya nair", phone="098765 43210", company="Zoho Corp")
    assert priya["full_name"] == "Priya Nair"

    person = ok(await a.get(f"/v1/contacts/{priya['id']}"))
    assert person["phones"] == ["+919876543210"]  # normalised to E.164
    assert person["company"] == "Zoho Corp"

    # Same phone again: a duplicate, not a second person.
    dup = await a.post("/v1/contacts", {"full_name": "P Nair", "phone": "+91 98765 43210"})
    assert dup.status_code == 409
    assert dup.json()["error"]["code"] == "CONTACT_EXISTS"

    edited = ok(await a.patch(f"/v1/contacts/{priya['id']}", {"title": "SDE 2", "city": "Pune"}))
    assert (edited["title"], edited["city"]) == ("SDE 2", "Pune")

    memory = ok(await a.post(f"/v1/contacts/{priya['id']}/memories", {"text": "Met at eChai"}), 201)
    person = ok(await a.get(f"/v1/contacts/{priya['id']}"))
    assert [m["text"] for m in person["memories"]] == ["Met at eChai"]
    ok(await a.delete(f"/v1/memories/{memory['id']}"), 204)

    ok(await a.delete(f"/v1/contacts/{priya['id']}"), 204)
    assert (await a.get(f"/v1/contacts/{priya['id']}")).status_code == 404
    assert ok(await a.get("/v1/contacts"))["items"] == []


async def test_contact_validation(users: MakeUser) -> None:
    a = await users()
    await a.onboard()
    for body in ({"full_name": ""}, {"full_name": "   "}, {"full_name": "x" * 500}):
        res = await a.post("/v1/contacts", body)
        assert res.status_code == 422, body
        assert res.json()["error"]["code"] == "VALIDATION_ERROR"
    bad_phone = await a.post("/v1/contacts", {"full_name": "Asha", "phone": "12"})
    assert bad_phone.status_code == 422


async def test_contacts_search_and_paging(users: MakeUser, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(contacts_svc, "PAGE_SIZE", 5)
    a = await users()
    await a.onboard()
    for i in range(7):
        await a.contact(f"Person {i:02d}", company="Zoho" if i % 2 else "Infosys")
    first = ok(await a.get("/v1/contacts"))
    assert len(first["items"]) == 5 and first["next_cursor"]
    rest = ok(await a.get("/v1/contacts", params={"cursor": first["next_cursor"]}))
    names = [c["full_name"] for c in first["items"] + rest["items"]]
    assert names == [f"Person {i:02d}" for i in range(7)]
    assert rest["next_cursor"] is None
    zoho = ok(await a.get("/v1/contacts", params={"q": "zoho"}))
    assert len(zoho["items"]) == 3


async def test_linkedin_import_preview_then_idempotent_commit(users: MakeUser) -> None:
    a = await users()
    await a.onboard()
    await a.contact("Kavya Rao", linkedin_url="linkedin.com/in/kavya-rao-it")
    preview = ok(
        await a.post("/v1/imports/file", files={"file": ("Connections.csv", LINKEDIN_CSV)}), 201
    )
    assert preview["source"] == "linkedin_csv"
    assert preview["counts"] == {"new": 1, "merged": 1, "skipped": 1}
    first = ok(await a.post(f"/v1/imports/{preview['id']}/commit"))
    again = ok(await a.post(f"/v1/imports/{preview['id']}/commit"))
    assert first["counts"] == again["counts"]
    names = sorted(c["full_name"] for c in ok(await a.get("/v1/contacts"))["items"])
    assert names == ["Imran Shaikh", "Kavya Rao"]


async def test_import_rejects_unreadable_files(users: MakeUser) -> None:
    a = await users()
    await a.onboard()
    res = await a.post("/v1/imports/file", files={"file": ("notes.csv", "name,phone\nA,1\n")})
    assert res.status_code == 422
    assert res.json()["error"]["code"] == "IMPORT_FILE_INVALID"


async def test_import_needs_contacts_consent(users: MakeUser) -> None:
    a = await users()
    ok(await a.put("/v1/privacy/consents", {"accept_notice": True, "consents": {}}))
    res = await a.post(
        "/v1/imports/picker", {"contacts": [{"name": ["Asha"], "tel": ["+919000000001"]}]}
    )
    assert res.status_code == 403
    assert res.json()["error"]["code"] == "CONSENT_REQUIRED"


async def test_people_are_invisible_to_other_users(users: MakeUser) -> None:
    a, b = await users(), await users()
    await a.onboard()
    await b.onboard()
    priya = await a.contact("Priya Nair", phone="+919876543210")
    memory = ok(await a.post(f"/v1/contacts/{priya['id']}/memories", {"text": "secret"}), 201)
    preview = ok(
        await a.post("/v1/imports/file", files={"file": ("Connections.csv", LINKEDIN_CSV)}), 201
    )

    cid, mid, iid = priya["id"], memory["id"], preview["id"]
    probes = [
        await b.get(f"/v1/contacts/{cid}"),
        await b.patch(f"/v1/contacts/{cid}", {"title": "hacked"}),
        await b.delete(f"/v1/contacts/{cid}"),
        await b.post(f"/v1/contacts/{cid}/memories", {"text": "x"}),
        await b.post(f"/v1/contacts/{cid}/draft", {"stage": "warm_up"}),
        await b.delete(f"/v1/memories/{mid}"),
        await b.get(f"/v1/imports/{iid}"),
        await b.post(f"/v1/imports/{iid}/commit"),
    ]
    assert [p.status_code for p in probes] == [404] * len(probes)
    assert ok(await b.get("/v1/contacts"))["items"] == []
    assert ok(await b.get("/v1/contacts", params={"q": "Priya"}))["items"] == []

    # B can hold the same phone number: dedupe is per user.
    await b.contact("Priya N", phone="+919876543210")
    # A's data is untouched.
    person = ok(await a.get(f"/v1/contacts/{cid}"))
    assert person["title"] is None and [m["text"] for m in person["memories"]] == ["secret"]
    assert (await a.get(f"/v1/imports/{iid}")).status_code == 200
    assert (await b.get(f"/v1/contacts/{uuid.uuid4()}")).status_code == 404
