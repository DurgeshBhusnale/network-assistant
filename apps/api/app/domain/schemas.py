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
