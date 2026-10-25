"""Request/response models for /v1 (Sprint 1: profile, packs, goals, consents)."""

import uuid
from datetime import date, datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

Language = Literal["en", "hinglish", "hi", "mr"]
OnboardingStep = Literal["goal", "import", "style", "done"]
ConsentKind = Literal["contacts", "voice", "whatsapp", "analytics"]
GoalStatus = Literal["active", "paused", "done"]


class _In(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ProfileOut(BaseModel):
    user_id: uuid.UUID
    email: str | None
    display_name: str | None
    language: Language
    timezone: str
    nudge_time: str = Field(description="HH:MM in the user's timezone")
    onboarding_step: OnboardingStep
    privacy_notice_accepted: bool
    whatsapp_linked: bool


class ProfileUpdate(_In):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    language: Language | None = None
    timezone: str | None = None
    nudge_time: time | None = None
    onboarding_step: OnboardingStep | None = None

    @field_validator("display_name")
    @classmethod
    def _strip(cls, value: str | None) -> str | None:
        return value.strip() if value else value

    @field_validator("timezone")
    @classmethod
    def _known_timezone(cls, value: str | None) -> str | None:
        if value is None:
            return value
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("unknown timezone") from exc
        return value


class PackOut(BaseModel):
    id: str
    name: str
    status: Literal["active", "coming_soon", "retired"]
    sort_order: int
    picker_label: str
    tagline: str | None
    duration_days: int | None
    goal_schema: dict[str, Any] | None
    stages: list[dict[str, Any]]
    copy_text: dict[str, Any] = Field(description="Pack UI copy (labels, descriptions)")


class GoalCreate(_In):
    pack_id: str
    params: dict[str, Any]


class GoalUpdate(_In):
    params: dict[str, Any] | None = None
    status: GoalStatus | None = None


class GoalOut(BaseModel):
    id: uuid.UUID
    pack_id: str
    params: dict[str, Any]
    status: GoalStatus
    starts_on: date
    ends_on: date | None
    day_number: int = Field(description="1-based day of the goal in the user's timezone")
    days_left: int | None


class ConsentState(BaseModel):
    granted: bool
    version: str | None
    granted_at: datetime | None


class ConsentsOut(BaseModel):
    notice_version: str
    notice_accepted: bool
    consents: dict[ConsentKind, ConsentState]


class ConsentsUpdate(_In):
    accept_notice: bool
    consents: dict[ConsentKind, bool]


# --- People (Sprint 2) ---------------------------------------------------------------------

ImportSource = Literal["picker", "vcard", "linkedin_csv", "manual"]


class ContactSummary(BaseModel):
    id: uuid.UUID
    full_name: str
    title: str | None
    company: str | None
    city: str | None
    how_known: str | None
    has_phone: bool
    has_linkedin: bool


class ContactList(BaseModel):
    items: list[ContactSummary]
    next_cursor: str | None


class ContactCreate(_In):
    full_name: str = Field(min_length=1, max_length=200)
    phone: str | None = Field(default=None, max_length=40)
    email: str | None = Field(default=None, max_length=254)
    linkedin_url: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    how_known: str | None = Field(default=None, max_length=300)
    birthday: date | None = None


class ContactUpdate(_In):
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    phones: list[str] | None = Field(default=None, max_length=10)
    emails: list[str] | None = Field(default=None, max_length=10)
    linkedin_url: str | None = Field(default=None, max_length=300)
    company: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    city: str | None = Field(default=None, max_length=80)
    how_known: str | None = Field(default=None, max_length=300)
    birthday: date | None = None


class MemoryOut(BaseModel):
    id: uuid.UUID
    text: str
    source: Literal["note", "voice", "whatsapp", "import"]
    created_at: datetime


class MemoryCreate(_In):
    text: str = Field(min_length=1, max_length=2000)


class HistoryItem(BaseModel):
    kind: str = Field(description="Interaction type, or 'added' for when the person was added")
    channel: str | None = None
    stage: str | None = None
    outcome: str | None = None
    sources: list[ImportSource] = Field(default_factory=list)
    occurred_at: datetime


class NextStep(BaseModel):
    goal_label: str
    stage: str | None
    stage_label: str | None


class PersonOut(BaseModel):
    id: uuid.UUID
    full_name: str
    first_name: str | None
    last_name: str | None
    phones: list[str]
    emails: list[str]
    linkedin_url: str | None
    company: str | None
    title: str | None
    city: str | None
    how_known: str | None
    birthday: date | None
    sources: list[ImportSource]
    memories: list[MemoryOut]
    history: list[HistoryItem]
    next_step: NextStep | None


class PickerContact(BaseModel):
    name: list[str] = Field(default_factory=list, max_length=5)
    tel: list[str] = Field(default_factory=list, max_length=10)
    email: list[str] = Field(default_factory=list, max_length=10)


class PickerImport(_In):
    contacts: list[PickerContact] = Field(min_length=1, max_length=2000)


class ImportCounts(BaseModel):
    new: int = 0
    merged: int = 0
    skipped: int = 0


class ImportRowError(BaseModel):
    row: int
    reason: str


class ImportOut(BaseModel):
    id: uuid.UUID
    source: ImportSource
    status: Literal["queued", "processing", "ready", "committed", "failed"]
    counts: ImportCounts
    errors: list[ImportRowError]
    created_at: datetime


# --- Drafting (Sprint 3) -------------------------------------------------------------------

Tone = Literal["shorter", "warmer", "formal", "hinglish"]


class StyleOut(BaseModel):
    samples: list[str]
    summary: str | None


class StyleSamplesUpdate(_In):
    samples: list[str] = Field(min_length=0, max_length=10)

    @field_validator("samples")
    @classmethod
    def _clean_samples(cls, value: list[str]) -> list[str]:
        cleaned = [s.strip() for s in value if s.strip()]
        if any(len(s) > 1000 for s in cleaned):
            raise ValueError("each sample must be at most 1000 characters")
        return cleaned


class DraftCreate(_In):
    stage: str = Field(min_length=1, max_length=40)
    tone: Tone | None = None


class DraftRegenerate(_In):
    tone: Tone | None = Field(default=None, description="None = Another version")


class DraftEdit(_In):
    final_text: str = Field(min_length=1, max_length=2000)


class DraftOut(BaseModel):
    id: uuid.UUID
    contact_id: uuid.UUID
    stage: str
    stage_label: str
    step: int
    total_steps: int
    tone: Tone | None
    language: str
    text: str
    final_text: str | None
    word_count: int
    unsupported_claims: list[str]
    warnings: list[str]
    reasons: list[str]
    regenerations: int
    regenerations_left: int | None
    drafts_left_this_month: int | None
    created_at: datetime
