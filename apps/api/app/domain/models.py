"""SQLAlchemy models. Column names mirror supabase/migrations; never return these from routes."""

import uuid
from datetime import date, datetime, time
from typing import Any, ClassVar

from sqlalchemy import BigInteger, Date, DateTime, Enum, ForeignKey, Integer, String, Text, Time
from sqlalchemy.dialects.postgresql import JSONB, UUID
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
