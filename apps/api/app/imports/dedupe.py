"""Dedupe and merge (FR-CON-5). Pure.

Match order: phone, then email, then LinkedIn URL. Never on name alone. Candidates that match
an existing contact merge into it; candidates that match an earlier candidate in the same import
merge into that one.
"""

import uuid
from dataclasses import dataclass, field
from datetime import date

from app.imports.models import Candidate


@dataclass
class ContactFields:
    """The mergeable fields of a contact (existing or about to be created)."""

    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    phones: list[str] = field(default_factory=list)
    emails: list[str] = field(default_factory=list)
    linkedin_url: str | None = None
    company: str | None = None
    company_norm: str | None = None
    title: str | None = None
    birthday: date | None = None
    sources: list[str] = field(default_factory=list)

    @classmethod
    def from_candidate(cls, c: Candidate) -> "ContactFields":
        return cls(
            full_name=c.full_name,
            first_name=c.first_name,
            last_name=c.last_name,
            phones=list(c.phones),
            emails=list(c.emails),
            linkedin_url=c.linkedin_url,
            company=c.company,
            company_norm=c.company_norm,
            title=c.title,
            birthday=c.birthday,
            sources=[c.source],
        )


@dataclass
class MergeResult:
    changed: bool
    job_changed: bool


def merge_into(target: ContactFields, incoming: Candidate) -> MergeResult:
    """Union arrays, fill empty scalars, never overwrite a value with an empty one.

    A different company on an already-known contact is a job change: company and title take the
    incoming values and the caller records a `job_change` trigger.
    """
    changed = False
    for attr in ("phones", "emails"):
        current: list[str] = getattr(target, attr)
        added = [v for v in getattr(incoming, attr) if v not in current]
        if added:
            setattr(target, attr, current + added)
            changed = True
    for attr in ("first_name", "last_name", "linkedin_url", "birthday"):
        if getattr(target, attr) is None and getattr(incoming, attr) is not None:
            setattr(target, attr, getattr(incoming, attr))
            changed = True
    job_changed = False
    if incoming.company_norm:
        if not target.company_norm:
            target.company, target.company_norm = incoming.company, incoming.company_norm
            changed = True
        elif target.company_norm != incoming.company_norm:
            target.company, target.company_norm = incoming.company, incoming.company_norm
            target.title = incoming.title or target.title
            changed = job_changed = True
    if incoming.title and not target.title:
        target.title = incoming.title
        changed = True
    if incoming.source not in target.sources:
        target.sources = [*target.sources, incoming.source]
        changed = True
    return MergeResult(changed=changed, job_changed=job_changed)


@dataclass
class ExistingContact:
    id: uuid.UUID
    fields: ContactFields


@dataclass
class PlannedNew:
    fields: ContactFields
    rows: list[int]


@dataclass
class PlannedMerge:
    contact_id: uuid.UUID
    fields: ContactFields
    rows: list[int]
    changed: bool = False
    job_changed: bool = False


@dataclass
class ImportPlan:
    new: list[PlannedNew]
    merges: list[PlannedMerge]

    @property
    def counts(self) -> dict[str, int]:
        return {
            "new": len(self.new),
            "merged": sum(len(m.rows) for m in self.merges)
            + sum(len(n.rows) - 1 for n in self.new),
        }


class _Index:
    def __init__(self) -> None:
        self.by_key: dict[str, object] = {}

    @staticmethod
    def keys(f: ContactFields | Candidate) -> list[str]:
        keys = [f"p:{p}" for p in f.phones] + [f"e:{e}" for e in f.emails]
        if f.linkedin_url:
            keys.append(f"l:{f.linkedin_url}")
        return keys

    def find(self, c: Candidate) -> object | None:
        # Ordered: phones first, then emails, then LinkedIn (the order keys() returns).
        for key in self.keys(c):
            if key in self.by_key:
                return self.by_key[key]
        return None

    def add(self, f: ContactFields, target: object) -> None:
        for key in self.keys(f):
            self.by_key.setdefault(key, target)


def plan_import(candidates: list[Candidate], existing: list[ExistingContact]) -> ImportPlan:
    index = _Index()
    merges: dict[uuid.UUID, PlannedMerge] = {}
    for contact in existing:
        index.add(contact.fields, contact)
    new: list[PlannedNew] = []

    for c in candidates:
        target = index.find(c)
        if isinstance(target, ExistingContact):
            merge = merges.get(target.id)
            if merge is None:
                merge = merges[target.id] = PlannedMerge(
                    contact_id=target.id, fields=target.fields, rows=[]
                )
            result = merge_into(merge.fields, c)
            merge.rows.append(c.row)
            merge.changed |= result.changed
            merge.job_changed |= result.job_changed
            index.add(merge.fields, target)
        elif isinstance(target, PlannedNew):
            merge_into(target.fields, c)
            target.rows.append(c.row)
            index.add(target.fields, target)
        else:
            planned = PlannedNew(fields=ContactFields.from_candidate(c), rows=[c.row])
            new.append(planned)
            index.add(planned.fields, planned)
    return ImportPlan(new=new, merges=list(merges.values()))
