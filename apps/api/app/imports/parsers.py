"""Parsers for LinkedIn Connections.csv, vCard files and Contact Picker payloads. Pure."""

import csv
import io
import re
from datetime import date, datetime
from typing import Any

import vobject

from app.imports.models import Candidate, ImportSource, ParseResult, RowError
from app.imports.normalise import (
    clean_text,
    normalise_company,
    normalise_email,
    normalise_linkedin,
    normalise_phone,
    split_name,
    unique,
)

MAX_ROWS = 10_000
YEARLESS_BIRTHDAY_YEAR = 1904  # leap year placeholder when only month/day are known


class ImportFileError(ValueError):
    """The whole file is unusable (wrong format, too many rows)."""


def _candidate(
    row: int,
    source: ImportSource,
    *,
    full: str | None = None,
    first: str | None = None,
    last: str | None = None,
    phones: list[str] | None = None,
    emails: list[str] | None = None,
    linkedin: str | None = None,
    company: str | None = None,
    title: str | None = None,
    birthday: date | None = None,
    connected_on: date | None = None,
) -> Candidate | RowError:
    name = split_name(full, first, last)
    if name is None:
        return RowError(row=row, reason="No name")
    full_name, first_name, last_name = name
    company_c = clean_text(company)
    return Candidate(
        row=row,
        source=source,
        full_name=full_name[:200],
        first_name=first_name,
        last_name=last_name,
        phones=unique([normalise_phone(p) for p in phones or []]),
        emails=unique([normalise_email(e) for e in emails or []]),
        linkedin_url=normalise_linkedin(linkedin),
        company=company_c,
        company_norm=normalise_company(company_c),
        title=clean_text(title),
        birthday=birthday,
        connected_on=connected_on,
    )


def _collect(results: list[Candidate | RowError]) -> ParseResult:
    if len(results) > MAX_ROWS:
        raise ImportFileError(f"Too many rows (max {MAX_ROWS:,}).")
    return ParseResult(
        candidates=[r for r in results if isinstance(r, Candidate)],
        errors=[r for r in results if isinstance(r, RowError)],
    )


# --- LinkedIn Connections.csv --------------------------------------------------------------

_LINKEDIN_DATE_FORMATS = ("%d %b %Y", "%m/%d/%Y", "%d-%b-%y", "%Y-%m-%d")


def _parse_date(value: str | None, formats: tuple[str, ...]) -> date | None:
    value = clean_text(value)
    if not value:
        return None
    for fmt in formats:
        try:
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def parse_linkedin_csv(text: str) -> ParseResult:
    """LinkedIn's export starts with a 'Notes:' preamble; the header row has First Name and URL."""
    lines = text.lstrip("﻿").splitlines()
    header_at = next(
        (i for i, line in enumerate(lines) if "First Name" in line and "URL" in line), None
    )
    if header_at is None:
        raise ImportFileError(
            "Couldn't read that file. Upload the Connections.csv from LinkedIn's export."
        )
    reader = csv.DictReader(io.StringIO("\n".join(lines[header_at:])))
    results: list[Candidate | RowError] = []
    for index, raw in enumerate(reader, start=1):
        row = {(k or "").strip(): (v or "").strip() for k, v in raw.items()}
        if not any(row.values()):
            continue
        results.append(
            _candidate(
                index,
                "linkedin_csv",
                first=row.get("First Name"),
                last=row.get("Last Name"),
                emails=[row.get("Email Address", "")],
                linkedin=row.get("URL"),
                company=row.get("Company"),
                title=row.get("Position"),
                connected_on=_parse_date(row.get("Connected On"), _LINKEDIN_DATE_FORMATS),
            )
        )
    return _collect(results)


# --- vCard ---------------------------------------------------------------------------------

_BDAY_YEARLESS = re.compile(r"^--(\d{2})-?(\d{2})$")


def _parse_bday(value: Any) -> date | None:
    if isinstance(value, date):
        return value
    text = clean_text(str(value)) if value else None
    if not text:
        return None
    yearless = _BDAY_YEARLESS.match(text)
    if yearless:
        try:
            return date(YEARLESS_BIRTHDAY_YEAR, int(yearless[1]), int(yearless[2]))
        except ValueError:
            return None
    return _parse_date(text[:10], ("%Y-%m-%d", "%Y%m%d", "%d/%m/%Y"))


def _values(card: Any, name: str) -> list[Any]:
    return [c.value for c in card.contents.get(name, [])]


def parse_vcard(text: str) -> ParseResult:
    results: list[Candidate | RowError] = []
    try:
        cards = list(vobject.readComponents(text, ignoreUnreadable=True))
    except Exception as exc:
        raise ImportFileError("Couldn't read that file. Upload a .vcf contacts file.") from exc
    if not cards:
        raise ImportFileError("No contacts found in that file.")
    for index, card in enumerate(cards, start=1):
        fn = next(iter(_values(card, "fn")), None)
        n = next(iter(_values(card, "n")), None)
        org = next(iter(_values(card, "org")), None)
        company = (org[0] if isinstance(org, list) and org else org) or None
        results.append(
            _candidate(
                index,
                "vcard",
                full=str(fn) if fn else None,
                first=getattr(n, "given", None) or None,
                last=getattr(n, "family", None) or None,
                phones=[str(v) for v in _values(card, "tel")],
                emails=[str(v) for v in _values(card, "email")],
                linkedin=next(
                    (str(u) for u in _values(card, "url") if "linkedin.com" in str(u)), None
                ),
                company=str(company) if company else None,
                title=next((str(t) for t in _values(card, "title")), None),
                birthday=_parse_bday(next(iter(_values(card, "bday")), None)),
            )
        )
    return _collect(results)


# --- Contact Picker (navigator.contacts.select) ---------------------------------------------


def parse_picker(items: list[dict[str, list[str]]]) -> ParseResult:
    results: list[Candidate | RowError] = []
    for index, item in enumerate(items, start=1):
        names = [n for n in item.get("name", []) if n and n.strip()]
        results.append(
            _candidate(
                index,
                "picker",
                full=names[0] if names else None,
                phones=item.get("tel", []),
                emails=item.get("email", []),
            )
        )
    return _collect(results)
