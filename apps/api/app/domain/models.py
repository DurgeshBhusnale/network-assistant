"""SQLAlchemy models. Column names mirror supabase/migrations; never return these from routes."""

import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any, ClassVar

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    type_annotation_map: ClassVar[dict[Any, Any]] = {
        dict[str, Any]: JSONB,
        uuid.UUID: UUID(as_uuid=True),
    }


def _pg_enum(name: str, *values: str) -> Enum:
    return Enum(*values, name=name, create_type=False)


GOAL_STATUS = _pg_enum("goal_status", "active", "paused", "done")
PACK_STATUS = _pg_enum("pack_status", "active", "coming_soon", "retired")
CONSENT_TYPE = _pg_enum("consent_type", "contacts", "voice", "whatsapp", "analytics")


class Profile(Base):
    __tablename__ = "profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    display_name: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, server_default="en")
    timezone: Mapped[str] = mapped_column(Text, server_default="Asia/Kolkata")
    nudge_time: Mapped[time] = mapped_column(Time, server_default="09:00")
    onboarding_step: Mapped[str] = mapped_column(Text, server_default="goal")
    privacy_notice_version: Mapped[str | None] = mapped_column(Text)
    privacy_notice_ack_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wa_phone_e164: Mapped[str | None] = mapped_column(Text)
    wa_opt_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wa_opt_out_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    wa_last_inbound_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    email_digest: Mapped[bool] = mapped_column(Boolean, server_default="true")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Pack(Base):
    __tablename__ = "packs"

    id: Mapped[str] = mapped_column(Text, primary_key=True)
    name: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(PACK_STATUS)
    sort_order: Mapped[int] = mapped_column(Integer)
    config: Mapped[dict[str, Any]] = mapped_column(JSONB)


class Goal(Base):
    __tablename__ = "goals"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    pack_id: Mapped[str] = mapped_column(ForeignKey("packs.id"))
    params: Mapped[dict[str, Any]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(GOAL_STATUS, server_default="active")
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    type: Mapped[str] = mapped_column(CONSENT_TYPE)
    version: Mapped[str] = mapped_column(Text)
    granted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    withdrawn_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Event(Base):
    __tablename__ = "events"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column()
    name: Mapped[str] = mapped_column(String)
    props: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


IMPORT_SOURCE = _pg_enum("import_source", "picker", "vcard", "linkedin_csv", "manual")
JOB_STATUS = _pg_enum("job_status", "queued", "processing", "ready", "committed", "failed")
MEMORY_SOURCE = _pg_enum("memory_source", "note", "voice", "whatsapp", "import")


class Contact(Base):
    __tablename__ = "contacts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    full_name: Mapped[str] = mapped_column(Text)
    first_name: Mapped[str | None] = mapped_column(Text)
    last_name: Mapped[str | None] = mapped_column(Text)
    phones: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    emails: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    linkedin_url: Mapped[str | None] = mapped_column(Text)
    company: Mapped[str | None] = mapped_column(Text)
    company_norm: Mapped[str | None] = mapped_column(Text)
    title: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str | None] = mapped_column(Text)
    how_known: Mapped[str | None] = mapped_column(Text)
    birthday: Mapped[date | None] = mapped_column(Date)
    sources: Mapped[list[str]] = mapped_column(ARRAY(IMPORT_SOURCE), server_default="{}")
    last_interaction_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"))
    text: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(MEMORY_SOURCE)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Interaction(Base):
    __tablename__ = "interactions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"))
    goal_id: Mapped[uuid.UUID | None] = mapped_column()
    type: Mapped[str] = mapped_column(Text)
    stage: Mapped[str | None] = mapped_column(Text)
    outcome: Mapped[str | None] = mapped_column(Text)
    channel: Mapped[str | None] = mapped_column(Text)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")


class ImportJob(Base):
    __tablename__ = "imports"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    source: Mapped[str] = mapped_column(IMPORT_SOURCE)
    status: Mapped[str] = mapped_column(JOB_STATUS, server_default="queued")
    counts: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    errors: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    preview: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Trigger(Base):
    __tablename__ = "triggers"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"))
    type: Mapped[str] = mapped_column(Text)
    date: Mapped[date] = mapped_column(Date)


class AICall(Base):
    __tablename__ = "ai_calls"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[uuid.UUID | None] = mapped_column()
    task: Mapped[str] = mapped_column(Text)
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    tokens_in: Mapped[int | None] = mapped_column(Integer)
    tokens_out: Mapped[int | None] = mapped_column(Integer)
    audio_seconds: Mapped[float | None] = mapped_column(Float)
    cost_inr: Mapped[Decimal | None] = mapped_column(Numeric(10, 4))
    latency_ms: Mapped[int | None] = mapped_column(Integer)
    ok: Mapped[bool] = mapped_column(Boolean)


class StyleProfile(Base):
    __tablename__ = "style_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    samples: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}")
    summary: Mapped[str | None] = mapped_column(Text)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    suggestion_id: Mapped[uuid.UUID | None] = mapped_column()
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"))
    stage: Mapped[str] = mapped_column(Text)
    tone: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str] = mapped_column(Text, server_default="en")
    provider: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(Text)
    prompt_version: Mapped[str] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text)
    final_text: Mapped[str | None] = mapped_column(Text)
    regenerations: Mapped[int] = mapped_column(Integer, server_default="0")
    factcheck: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")
    sent_channel: Mapped[str | None] = mapped_column(Text)
    send_opened_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Entitlement(Base):
    __tablename__ = "entitlements"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    product: Mapped[str] = mapped_column(
        _pg_enum("product_code", "sprint", "pro_monthly", "pro_yearly")
    )
    starts_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")
    ends_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    drafts_used: Mapped[int] = mapped_column(Integer, server_default="0")
    source_payment_id: Mapped[uuid.UUID | None] = mapped_column()


SUGGESTION_STATUS = _pg_enum(
    "suggestion_status", "pending", "opened", "sent", "snoozed", "dismissed", "expired"
)


class Suggestion(Base):
    __tablename__ = "suggestions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    goal_id: Mapped[uuid.UUID | None] = mapped_column()
    contact_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("contacts.id"))
    for_date: Mapped[date] = mapped_column(Date)
    score: Mapped[float] = mapped_column(Float)
    reasons: Mapped[list[Any]] = mapped_column(JSONB, server_default="[]")
    stage: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(SUGGESTION_STATUS, server_default="pending")
    snoozed_until: Mapped[date | None] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class GoalContact(Base):
    __tablename__ = "goal_contacts"

    goal_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    contact_id: Mapped[uuid.UUID] = mapped_column(primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column()
    relevance_label: Mapped[str | None] = mapped_column(Text)
    relevance: Mapped[float | None] = mapped_column(Float)
    relevance_reason: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(Text, server_default="none")
    outcome: Mapped[str | None] = mapped_column(Text)
    last_suggested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    thanked_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dismissed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class CalendarEvent(Base):
    __tablename__ = "calendar_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    date: Mapped[date] = mapped_column(Date)
    name: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean)


CAPTURE_SOURCE = _pg_enum("capture_source", "app_audio", "app_text", "wa_audio", "wa_text")


class Capture(Base):
    __tablename__ = "captures"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    source: Mapped[str] = mapped_column(CAPTURE_SOURCE)
    storage_path: Mapped[str | None] = mapped_column(Text)
    wa_media_id: Mapped[str | None] = mapped_column(Text)
    language: Mapped[str | None] = mapped_column(Text)
    transcript: Mapped[str | None] = mapped_column(Text)
    extracted: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(JOB_STATUS, server_default="queued")
    error: Mapped[str | None] = mapped_column(Text)
    audio_deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_ref: Mapped[str] = mapped_column(Text)
    action: Mapped[str] = mapped_column(Text)
    meta: Mapped[dict[str, Any]] = mapped_column(JSONB, server_default="{}")


class WaLinkCode(Base):
    __tablename__ = "wa_link_codes"

    code: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column()
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class WaMessage(Base):
    """Metadata only. Message bodies are never stored (CLAUDE.md rule 7)."""

    __tablename__ = "wa_messages"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID | None] = mapped_column()
    direction: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(Text)
    template_name: Mapped[str | None] = mapped_column(Text)
    wa_message_id: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID | None] = mapped_column()
    provider: Mapped[str] = mapped_column(Text, server_default="razorpay")
    product: Mapped[str] = mapped_column(
        _pg_enum("product_code", "sprint", "pro_monthly", "pro_yearly")
    )
    amount_paise: Mapped[int] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(Text, server_default="INR")
    status: Mapped[str] = mapped_column(Text, server_default="created")
    provider_order_id: Mapped[str | None] = mapped_column(Text)
    provider_payment_id: Mapped[str | None] = mapped_column(Text)
    raw_event_id: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default="now()")


class PushSubscription(Base):
    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, server_default="gen_random_uuid()")
    user_id: Mapped[uuid.UUID] = mapped_column()
    endpoint: Mapped[str] = mapped_column(Text)
    keys: Mapped[dict[str, Any]] = mapped_column(JSONB)
