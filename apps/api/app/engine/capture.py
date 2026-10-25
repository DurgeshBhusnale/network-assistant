"""Capture extraction results → confirm-card candidates (FR-MEM-2/3/6). Pure.

Matching suggests possible existing contacts by name (+ company); it never merges on its own.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Any

from pydantic import BaseModel, Field
from rapidfuzz import fuzz

from app.imports.normalise import clean_text, normalise_company, split_name

MATCH_THRESHOLD = 85
MAX_MATCHES = 3
MAX_FOLLOW_UP_DAYS = 365


class ExtractedPerson(BaseModel):
    first_name: str = ""
    last_name: str | None = None
    company: str | None = None
    title: str | None = None
    where_met: str | None = None
    facts: list[str] = Field(default_factory=list)
    commitments: list[str] = Field(default_factory=list)
    follow_up_date: str | None = None


class ExtractResult(BaseModel):
    people: list[ExtractedPerson] = Field(default_factory=list)
    unassigned_facts: list[str] = Field(default_factory=list)


@dataclass(frozen=True)
class KnownContact:
    contact_id: str
    full_name: str
    company_norm: str | None


def valid_follow_up(value: str | None, capture_day: date) -> date | None:
    """ISO date on or after the capture day and within a year; anything else is dropped."""
    if not value:
        return None
    try:
        day = date.fromisoformat(value[:10])
    except ValueError:
        return None
    if day < capture_day or day > capture_day + timedelta(days=MAX_FOLLOW_UP_DAYS):
        return None
    return day


def matches_for(
    full_name: str, company_norm: str | None, known: list[KnownContact]
) -> list[dict[str, Any]]:
    """Possible existing contacts: token-set name similarity, nudged by company agreement."""
    scored: list[tuple[float, KnownContact]] = []
    for k in known:
        score = float(fuzz.token_set_ratio(full_name.lower(), k.full_name.lower()))
        if company_norm and k.company_norm:
            score += 5 if company_norm == k.company_norm else -15
        if score >= MATCH_THRESHOLD:
            scored.append((min(score, 100.0), k))
    scored.sort(key=lambda pair: -pair[0])
    return [
        {"contact_id": k.contact_id, "full_name": k.full_name, "score": round(score)}
        for score, k in scored[:MAX_MATCHES]
    ]


def _clean_list(values: list[str]) -> list[str]:
    out: list[str] = []
    for v in values:
        c = clean_text(v)
        if c and c not in out:
            out.append(c[:300])
    return out


def build_candidates(
    result: ExtractResult,
    known: list[KnownContact],
    capture_day: date,
    for_contact: KnownContact | None = None,
) -> dict[str, Any]:
    """The JSON stored in captures.extracted and shown as confirm cards."""
    people: list[dict[str, Any]] = []
    dropped = 0
    for index, p in enumerate(result.people):
        name = split_name(None, p.first_name, p.last_name)
        if name is None:
            dropped += 1
            continue
        full_name, first, last = name
        company = clean_text(p.company)
        company_norm = normalise_company(company)
        matches = (
            [
                {
                    "contact_id": for_contact.contact_id,
                    "full_name": for_contact.full_name,
                    "score": 100,
                }
            ]
            if for_contact is not None
            else matches_for(full_name, company_norm, known)
        )
        follow_up = valid_follow_up(p.follow_up_date, capture_day)
        people.append(
            {
                "key": f"p{index}",
                "full_name": full_name,
                "first_name": first,
                "last_name": last,
                "company": company,
                "title": clean_text(p.title),
                "where_met": clean_text(p.where_met),
                "facts": _clean_list(p.facts),
                "commitments": _clean_list(p.commitments),
                "follow_up_date": follow_up.isoformat() if follow_up else None,
                "matches": matches,
            }
        )
    if for_contact is not None and not people and (result.unassigned_facts or result.people):
        # A voice memory about one person: attach everything to them.
        people.append(
            {
                "key": "p0",
                "full_name": for_contact.full_name,
                "first_name": None,
                "last_name": None,
                "company": None,
                "title": None,
                "where_met": None,
                "facts": _clean_list(result.unassigned_facts),
                "commitments": [],
                "follow_up_date": None,
                "matches": [
                    {
                        "contact_id": for_contact.contact_id,
                        "full_name": for_contact.full_name,
                        "score": 100,
                    }
                ],
            }
        )
    return {
        "people": people,
        "unassigned_facts": _clean_list(result.unassigned_facts),
        "dropped": dropped,
    }


def memory_texts(facts: list[str], commitments: list[str], where_met: str | None) -> list[str]:
    texts = [f"Met at {where_met}"] if where_met else []
    texts += facts
    texts += [f"You promised: {c}" for c in commitments]
    return [t[:2000] for t in texts if t.strip()]
