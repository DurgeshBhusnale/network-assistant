"""Import data shapes. Pure."""

from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

ImportSource = Literal["picker", "vcard", "linkedin_csv", "manual"]


class Candidate(BaseModel):
    """One normalised person from an import source, before dedupe."""

    row: int = Field(description="1-based row/card number in the source, for error messages")
    source: ImportSource
    full_name: str
    first_name: str | None = None
    last_name: str | None = None
    phones: list[str] = Field(default_factory=list)
    emails: list[str] = Field(default_factory=list)
    linkedin_url: str | None = None
    company: str | None = None
    company_norm: str | None = None
    title: str | None = None
    birthday: date | None = None
    connected_on: date | None = None


class RowError(BaseModel):
    row: int
    reason: str


class ParseResult(BaseModel):
    candidates: list[Candidate]
    errors: list[RowError]
