import uuid
from datetime import date

import pytest

from app.imports.dedupe import ContactFields, ExistingContact, merge_into, plan_import
from app.imports.models import Candidate
from app.imports.normalise import (
    normalise_company,
    normalise_email,
    normalise_linkedin,
    normalise_phone,
)
from app.imports.parsers import (
    YEARLESS_BIRTHDAY_YEAR,
    ImportFileError,
    parse_linkedin_csv,
    parse_picker,
    parse_vcard,
)

# LinkedIn's real export: BOM, a Notes preamble, then the header row.
LINKEDIN_CSV = (
    "﻿Notes:\n"
    '"When exporting your connection data, you may notice that some of the email addresses are '
    'missing."\n'
    "\n"
    "First Name,Last Name,URL,Email Address,Company,Position,Connected On\n"
    "priya,nair,https://www.linkedin.com/in/Priya-Nair-123,,Zoho Corp,SDE 2,12 Mar 2024\n"
    'Arjun,,linkedin.com/in/arjunm/,arjun@Example.com,"Razorpay Software Pvt. Ltd.",,03/15/2023\n'
    ",,,,,,\n"
    ",,https://www.linkedin.com/in/ghost,,Acme,,\n"
)

VCARD = """BEGIN:VCARD
VERSION:3.0
FN:Ravi Kumar
N:Kumar;Ravi;;;
TEL;TYPE=CELL:+91 98765 43210
TEL;TYPE=HOME:098765 43210
EMAIL:ravi@example.com
ORG:Flipkart;Supply Chain
TITLE:Manager
BDAY:--0704
URL:https://www.linkedin.com/in/ravik
END:VCARD
BEGIN:VCARD
VERSION:3.0
FN:Sneha
TEL:12345
BDAY:1994-02-30
END:VCARD
"""


@pytest.mark.parametrize(
    ("fn", "raw", "expected"),
    [
        (normalise_phone, "098765 43210", "+919876543210"),
        (normalise_phone, "+1 (415) 555-2671", "+14155552671"),
        (normalise_phone, "12345", None),
        (normalise_phone, "", None),
        (normalise_email, " Priya@Example.COM ", "priya@example.com"),
        (normalise_email, "mailto:a@b.co", "a@b.co"),
        (normalise_email, "not-an-email", None),
        (normalise_linkedin, "linkedin.com/in/Priya-N/", "https://www.linkedin.com/in/priya-n"),
        (
            normalise_linkedin,
            "https://in.linkedin.com/in/priya%20n?trk=x",
            "https://www.linkedin.com/in/priya n",
        ),
        (normalise_linkedin, "https://www.linkedin.com/company/zoho", None),
        (normalise_linkedin, "https://evil-linkedin.com/in/x", None),
        (normalise_company, "Razorpay Software Pvt. Ltd.", "razorpay software"),
        (normalise_company, "Zoho Corporation", "zoho"),
        (normalise_company, "Tata Consultancy Services Limited", "tata consultancy services"),
        (normalise_company, "AT&T Inc.", "at&t"),
        (normalise_company, "  ", None),
    ],
)
def test_normalisers(fn: object, raw: str, expected: str | None) -> None:
    assert fn(raw) == expected  # type: ignore[operator]


def test_linkedin_csv_reads_the_real_export_shape() -> None:
    result = parse_linkedin_csv(LINKEDIN_CSV)
    assert [c.full_name for c in result.candidates] == ["Priya Nair", "Arjun"]
    priya, arjun = result.candidates
    assert priya.linkedin_url == "https://www.linkedin.com/in/priya-nair-123"
    assert priya.company_norm == "zoho"
    assert priya.connected_on == date(2024, 3, 12)
    assert priya.emails == []
    assert arjun.emails == ["arjun@example.com"]
    assert arjun.company_norm == "razorpay software"
    assert arjun.connected_on == date(2023, 3, 15)
    # Rows count blank lines too, matching what the user sees in a spreadsheet.
    assert [(e.row, e.reason) for e in result.errors] == [(4, "No name")]


def test_linkedin_csv_rejects_other_files() -> None:
    with pytest.raises(ImportFileError):
        parse_linkedin_csv("name,phone\nPriya,123\n")


def test_vcard_parses_phones_birthdays_and_org() -> None:
    result = parse_vcard(VCARD)
    ravi, sneha = result.candidates
    assert ravi.full_name == "Ravi Kumar"
    assert (ravi.first_name, ravi.last_name) == ("Ravi", "Kumar")
    assert ravi.phones == ["+919876543210"]  # two spellings of one number
    assert ravi.company == "Flipkart"
    assert ravi.birthday == date(YEARLESS_BIRTHDAY_YEAR, 7, 4)
    assert ravi.linkedin_url == "https://www.linkedin.com/in/ravik"
    assert sneha.phones == []  # invalid number dropped
    assert sneha.birthday is None  # 30 February


def test_vcard_rejects_garbage() -> None:
    with pytest.raises(ImportFileError):
        parse_vcard("hello world")


def test_picker_items() -> None:
    result = parse_picker(
        [
            {"name": ["Meera Iyer"], "tel": ["+91 99887 76655"], "email": []},
            {"name": [" "], "tel": ["+91 99887 76656"]},
        ]
    )
    assert [c.full_name for c in result.candidates] == ["Meera Iyer"]
    assert result.errors[0].reason == "No name"


def cand(row: int, name: str, **kw: object) -> Candidate:
    return Candidate(row=row, source=kw.pop("source", "picker"), full_name=name, **kw)  # type: ignore[arg-type]


def existing(name: str, **kw: object) -> ExistingContact:
    return ExistingContact(id=uuid.uuid4(), fields=ContactFields(full_name=name, **kw))  # type: ignore[arg-type]


def test_dedupe_matches_phone_email_linkedin_but_never_name_alone() -> None:
    by_phone = existing("Priya Nair", phones=["+919876543210"])
    by_email = existing("Arjun Mehta", emails=["arjun@example.com"])
    by_linkedin = existing("Ravi K", linkedin_url="https://www.linkedin.com/in/ravik")
    same_name_only = existing("Sneha Rao")
    plan = plan_import(
        [
            cand(1, "Priya N", phones=["+919876543210"], emails=["priya@example.com"]),
            cand(2, "Arjun", emails=["arjun@example.com"]),
            cand(3, "Ravi Kumar", linkedin_url="https://www.linkedin.com/in/ravik"),
            cand(4, "Sneha Rao", phones=["+919000000001"]),
        ],
        [by_phone, by_email, by_linkedin, same_name_only],
    )
    assert {m.contact_id for m in plan.merges} == {by_phone.id, by_email.id, by_linkedin.id}
    assert [n.fields.full_name for n in plan.new] == ["Sneha Rao"]
    merged_priya = next(m for m in plan.merges if m.contact_id == by_phone.id)
    assert merged_priya.fields.emails == ["priya@example.com"]
    assert merged_priya.fields.full_name == "Priya Nair"  # existing name kept
    assert plan.counts == {"new": 1, "merged": 3}


def test_dedupe_merges_duplicates_within_one_import() -> None:
    plan = plan_import(
        [
            cand(1, "Meera Iyer", phones=["+919988776655"]),
            cand(2, "Meera I", phones=["+919988776655"], emails=["meera@example.com"]),
            cand(3, "Meera", emails=["meera@example.com"], source="vcard"),
        ],
        [],
    )
    (only,) = plan.new
    assert only.rows == [1, 2, 3]
    assert only.fields.emails == ["meera@example.com"]
    assert only.fields.sources == ["picker", "vcard"]
    assert plan.counts == {"new": 1, "merged": 2}


@pytest.mark.parametrize(
    ("target_company", "incoming_company", "changed", "job_changed", "company"),
    [
        (None, "zoho", True, False, "zoho"),  # fills an empty company
        ("zoho", "zoho", False, False, "zoho"),
        ("zoho", "razorpay", True, True, "razorpay"),  # job change
        ("zoho", None, False, False, "zoho"),  # never overwrite with empty
    ],
)
def test_merge_company_and_job_change(
    target_company: str | None,
    incoming_company: str | None,
    changed: bool,
    job_changed: bool,
    company: str,
) -> None:
    target = ContactFields(
        full_name="Priya Nair",
        company=target_company,
        company_norm=target_company,
        title="SDE 2",
        sources=["picker"],
    )
    result = merge_into(
        target, cand(1, "Priya", company=incoming_company, company_norm=incoming_company)
    )
    assert (result.changed, result.job_changed) == (changed, job_changed)
    assert target.company_norm == company
    assert target.title == "SDE 2"  # no incoming title: kept even on a job change
