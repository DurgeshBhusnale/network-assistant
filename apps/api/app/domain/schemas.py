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
    email_digest: bool


class ProfileUpdate(_In):
    display_name: str | None = Field(default=None, min_length=1, max_length=80)
    language: Language | None = None
    timezone: str | None = None
    nudge_time: time | None = None
    onboarding_step: OnboardingStep | None = None
    email_digest: bool | None = None

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
    total: int | None = Field(
        default=None, description="Everyone in the list (ignores q); first page only"
    )


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


class SuggestionDraftIn(_In):
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
    sent_at: datetime | None = None
    sent_channel: str | None = None
    created_at: datetime


# --- Daily loop (Sprint 4) -----------------------------------------------------------------

StageTone = Literal["ask", "nurture", "thanks"]
SendChannel = Literal["whatsapp", "linkedin"]


class ReasonOut(BaseModel):
    text: str
    highlight: bool


class SuggestionContact(BaseModel):
    id: uuid.UUID
    full_name: str
    title: str | None
    company: str | None
    how_known: str | None


class SuggestionOut(BaseModel):
    id: uuid.UUID
    contact: SuggestionContact
    stage: str
    stage_label: str
    stage_tone: StageTone
    reasons: list[ReasonOut]
    status: Literal["pending", "opened", "sent", "snoozed", "dismissed", "expired"]
    draft_id: uuid.UUID | None


class StatOut(BaseModel):
    label: str
    value: str
    highlight: bool = False


class GoalStripOut(BaseModel):
    goal_id: uuid.UUID
    label: str
    title: str
    day_number: int
    total_days: int
    days_left: int | None
    stats: list[StatOut]
    success_count: int = Field(description="Outcomes reached so far (e.g. referrals)")
    success_target: int | None = Field(description="Goal target, when the pack has one")
    success_label: str = Field(description="Pack label for the outcome, e.g. 'Referrals'")


class TodayOut(BaseModel):
    date: date
    weekly: bool = Field(description="Free plan: one list per week (FR-TODAY-4)")
    display_name: str | None
    goal: GoalStripOut | None
    items: list[SuggestionOut]
    minutes: int
    contacts_count: int
    done: bool


class SnoozeIn(_In):
    days: Literal[1, 7]


class SendIn(_In):
    channel: SendChannel


class SendOut(BaseModel):
    open_url: str | None
    copy_text: str
    sends_left_today: int


class InteractionIn(_In):
    contact_id: uuid.UUID
    type: Literal["sent", "replied", "no_reply", "outcome"]
    outcome: str | None = Field(default=None, max_length=40)
    draft_id: uuid.UUID | None = None
    channel: Literal["whatsapp", "linkedin", "other"] | None = None


class InteractionOut(BaseModel):
    id: uuid.UUID
    type: str
    stage: str | None
    outcome: str | None
    occurred_at: datetime
    thank_suggestion: bool = False


class PendingReply(BaseModel):
    contact: SuggestionContact
    sent_at: datetime
    days_ago: int
    stage: str | None
    stage_label: str | None
    stage_has_ask: bool


class OutcomeOption(BaseModel):
    id: str
    label: str


class RepliesOut(BaseModel):
    items: list[PendingReply]
    outcomes: list[OutcomeOption]


class FunnelStep(BaseModel):
    key: str
    label: str
    count: int
    highlight: bool = False


class CompanyProgress(BaseModel):
    company: str
    people: int
    status: str
    reached: bool = Field(default=False, description="The pack's outcome was reached here")


class ProgressOut(BaseModel):
    goal: GoalStripOut | None
    headline: str | None
    warm_replies_this_week: int
    funnel: list[FunnelStep]
    by_company: list[CompanyProgress]


# --- Capture (Sprint 5) --------------------------------------------------------------------


class UploadUrlIn(_In):
    mime: Literal["audio/webm", "audio/ogg", "audio/mp4", "audio/mpeg", "audio/wav", "audio/aac"]


class UploadUrlOut(BaseModel):
    upload_url: str
    storage_path: str


class CaptureCreate(_In):
    text: str | None = Field(default=None, min_length=3, max_length=4000)
    storage_path: str | None = Field(default=None, max_length=300)
    language_hint: Literal["en", "hi", "mr", "hinglish"] | None = None
    contact_id: uuid.UUID | None = Field(default=None, description="Voice memory for this person")


class CaptureMatch(BaseModel):
    contact_id: uuid.UUID
    full_name: str
    score: int


class CaptureCandidate(BaseModel):
    key: str
    full_name: str
    first_name: str | None
    last_name: str | None
    company: str | None
    title: str | None
    where_met: str | None
    facts: list[str]
    commitments: list[str]
    follow_up_date: date | None
    matches: list[CaptureMatch]


class CaptureOut(BaseModel):
    id: uuid.UUID
    source: Literal["app_audio", "app_text", "wa_audio", "wa_text"]
    status: Literal["queued", "processing", "ready", "committed", "failed"]
    transcript: str | None
    people: list[CaptureCandidate]
    unassigned_facts: list[str]
    error: str | None
    for_contact_id: uuid.UUID | None


class CaptureDecision(_In):
    key: str = Field(max_length=10)
    action: Literal["new", "merge", "discard"]
    contact_id: uuid.UUID | None = None
    full_name: str | None = Field(default=None, min_length=1, max_length=200)
    company: str | None = Field(default=None, max_length=120)
    title: str | None = Field(default=None, max_length=120)
    facts: list[str] | None = Field(default=None, max_length=20)
    follow_up_date: date | None = None


class CaptureConfirm(_In):
    decisions: list[CaptureDecision] = Field(min_length=1, max_length=20)


class CaptureResult(BaseModel):
    created: int
    merged: int
    memories: int
    follow_ups: int
    contact_ids: list[uuid.UUID]


# --- Billing and notifications (Sprint 7) --------------------------------------------------

ProductCode = Literal["sprint", "pro_monthly", "pro_yearly"]


class PlanOption(BaseModel):
    product: ProductCode
    price_paise: int
    days: int
    enabled: bool


class PlansOut(BaseModel):
    products: list[PlanOption]
    checkout_key_id: str | None
    dev_checkout: bool = Field(description="Local only: payments are simulated (no Razorpay keys)")


class EntitlementOut(BaseModel):
    plan: Literal["free", "sprint", "pro"]
    ends_at: datetime | None
    days_left: int | None
    drafts_used: int | None
    fair_use_drafts: int | None
    free_drafts_left: int | None


class OrderIn(_In):
    product: ProductCode


class OrderOut(BaseModel):
    payment_id: uuid.UUID
    order_id: str
    amount_paise: int
    currency: str
    key_id: str | None
    product: ProductCode
    dev_checkout: bool


class CheckoutResultIn(_In):
    razorpay_order_id: str = Field(max_length=100)
    razorpay_payment_id: str = Field(max_length=100)
    razorpay_signature: str = Field(max_length=200)


class PaymentStatusOut(BaseModel):
    status: Literal["created", "paid", "failed", "refunded"]
    entitlement: EntitlementOut


class PushSubscriptionIn(_In):
    endpoint: str = Field(min_length=10, max_length=1000)
    keys: dict[str, str]


class PushConfigOut(BaseModel):
    public_key: str | None
