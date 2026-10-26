"""Inbound WhatsApp handling and the daily brief (FR-WA-1..7). Runs in the worker.

Every outbound message goes through WhatsAppClient's guard (rule 4). Messages from numbers not
linked to an account get no reply. Message bodies are never stored; capture text follows the
capture pipeline's own clearing rules.
"""

import logging
import uuid
from datetime import UTC, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine

from app.ai.router import AIRouter, AIUnavailableError
from app.analytics.track import track
from app.billing.limits import can_create_draft
from app.channels.whatsapp.client import RecipientNotAllowedError, WhatsAppClient, WhatsAppError
from app.channels.whatsapp.inbound import Inbound, SharedContact, brief_params, e164, parse_command
from app.core.config import Settings
from app.core.db import service_session
from app.core.storage import Storage
from app.domain.models import (
    Capture,
    Contact,
    Draft,
    Profile,
    Suggestion,
    WaLinkCode,
    WaMessage,
)
from app.domain.schemas import CaptureConfirm, CaptureDecision
from app.imports.parsers import parse_picker
from app.services import billing, captures, ranking
from app.services.consents import has_consent
from app.services.drafts import generate, load_context
from app.services.imports import commit_import, stage_import
from app.services.loop import active_goal_and_pack

logger = logging.getLogger(__name__)

DAILY_BRIEF = "daily_brief_v1"
MAX_AUDIO_BYTES = 16 * 1024 * 1024

HELP = (
    "I'm your [App name] assistant. Send me a note or a voice note after you meet someone and "
    "I'll save them for you.\n\nTODAY: who to contact today\nSTOP: no more messages\n"
    "HELP: this message\n\nI never message anyone but you."
)


def _now() -> datetime:
    return datetime.now(UTC)


async def _profile_by_phone(engine: AsyncEngine, phone: str) -> Profile | None:
    async with service_session(engine) as session:
        found: Profile | None = await session.scalar(
            select(Profile).where(Profile.wa_phone_e164 == phone)
        )
        return found


async def _link(engine: AsyncEngine, code: str, phone: str, now: datetime) -> uuid.UUID | None:
    async with service_session(engine) as session:
        row = await session.scalar(
            select(WaLinkCode).where(
                WaLinkCode.code == code, WaLinkCode.used_at.is_(None), WaLinkCode.expires_at > now
            )
        )
        if row is None:
            return None
        row.used_at = now
        # One number, one account: unlink it anywhere else first.
        await session.execute(
            update(Profile)
            .where(Profile.wa_phone_e164 == phone, Profile.user_id != row.user_id)
            .values(wa_phone_e164=None, wa_opt_in_at=None)
        )
        await session.flush()
        await session.execute(
            update(Profile)
            .where(Profile.user_id == row.user_id)
            .values(
                wa_phone_e164=phone, wa_opt_in_at=now, wa_opt_out_at=None, wa_last_inbound_at=now
            )
        )
        return row.user_id


async def _set_profile(engine: AsyncEngine, user_id: uuid.UUID, **values: Any) -> None:
    async with service_session(engine) as session:
        await session.execute(update(Profile).where(Profile.user_id == user_id).values(**values))


async def _attach(engine: AsyncEngine, wa_message_id: str, user_id: uuid.UUID) -> None:
    """Inbound metadata rows get the account once the sender is known (so deletion removes them)."""
    async with service_session(engine) as session:
        await session.execute(
            update(WaMessage)
            .where(WaMessage.wa_message_id == wa_message_id, WaMessage.user_id.is_(None))
            .values(user_id=user_id)
        )


async def handle_inbound(
    engine: AsyncEngine,
    router: AIRouter | None,
    wa: WhatsAppClient,
    settings: Settings,
    msg: Inbound,
) -> None:
    now = _now()
    phone = e164(msg.sender)
    command = parse_command(msg.text) if msg.kind == "text" else None

    if command is not None and command.kind == "link" and command.code:
        user_id = await _link(engine, command.code, phone, now)
        if user_id is not None:
            await _attach(engine, msg.id, user_id)
            await wa.send_text(
                user_id,
                "You're linked. Send me notes or voice notes after you meet people, or TODAY to "
                "see who to contact. Reply STOP anytime.",
            )
            await track(engine, user_id, "wa_linked", {})
        return

    profile = await _profile_by_phone(engine, phone)
    if profile is None or profile.wa_opt_in_at is None:
        logger.info("wa_unlinked_sender_ignored")  # rule 4: no reply to unlinked numbers
        return
    user_id = profile.user_id
    await _attach(engine, msg.id, user_id)
    await _set_profile(engine, user_id, wa_last_inbound_at=now)

    if command is not None and command.kind == "start":
        await _set_profile(engine, user_id, wa_opt_out_at=None, wa_opt_in_at=now)
        await wa.send_text(user_id, "Welcome back. You'll hear from me again. Reply STOP anytime.")
        return
    if profile.wa_opt_out_at is not None:
        return  # opted out: silence until START
    if command is not None and command.kind == "stop":
        await wa.send_text(
            user_id,
            "Done. I won't message you again. Send START to turn me back on.",
            allow_opted_out=True,
        )
        await _set_profile(engine, user_id, wa_opt_out_at=now)
        return
    if command is not None and command.kind == "help":
        await wa.send_text(user_id, HELP)
        return
    if command is not None and command.kind == "today":
        await _send_today(engine, wa, user_id, profile.timezone)
        return

    if msg.kind == "button" and msg.button_id:
        await _button(engine, router, wa, settings, user_id, profile.timezone, msg.button_id)
    elif msg.kind == "text" and msg.text and msg.text.strip():
        await _capture(engine, router, wa, settings, user_id, msg.text.strip(), None, "wa_text")
    elif msg.kind == "audio" and msg.media_id:
        await _voice(engine, router, wa, settings, user_id, msg)
    elif msg.kind == "contacts":
        await _contacts(engine, wa, user_id, profile.timezone, msg.contacts)
    else:
        await wa.send_text(user_id, HELP)


async def today_list(
    engine: AsyncEngine, user_id: uuid.UUID, timezone: str
) -> list[tuple[Suggestion, Contact]]:
    now = _now()
    today = now.astimezone(ZoneInfo(timezone)).date()
    async with service_session(engine) as session:
        plan = await billing.current_plan(session, user_id, now)
        for_date = ranking.week_start(today) if plan.kind == "free" else today
        found = await active_goal_and_pack(session, user_id)
        if found and not await ranking.has_list(session, user_id, for_date):
            await ranking.rank(session, user_id, found[0], found[1], today, for_date)
        rows = (
            await session.execute(
                select(Suggestion, Contact)
                .join(Contact, Contact.id == Suggestion.contact_id)
                .where(
                    Suggestion.user_id == user_id,
                    Suggestion.for_date == for_date,
                    Suggestion.status.in_(["pending", "opened"]),
                    Contact.deleted_at.is_(None),
                )
                .order_by(Suggestion.score.desc())
            )
        ).all()
    return [(s, c) for s, c in rows]


def _line(s: Suggestion, c: Contact) -> str:
    reason = next((r["text"] for r in s.reasons if isinstance(r, dict) and r.get("text")), None)
    return f"{c.full_name} — {reason}" if reason else c.full_name


async def _send_today(engine: AsyncEngine, wa: WhatsAppClient, user_id: uuid.UUID, tz: str) -> None:
    items = await today_list(engine, user_id, tz)
    if not items:
        await wa.send_text(
            user_id, "No one to contact right now. Send me a note after you meet someone."
        )
        return
    lines = "\n".join(f"• {_line(s, c)}" for s, c in items[:5])
    await wa.send_buttons(
        user_id,
        f"Today:\n{lines}",
        [("show_drafts", "Show drafts"), ("snooze_today", "Snooze today")],
    )


async def _button(
    engine: AsyncEngine,
    router: AIRouter | None,
    wa: WhatsAppClient,
    settings: Settings,
    user_id: uuid.UUID,
    timezone: str,
    button_id: str,
) -> None:
    if button_id == "snooze_today":
        tomorrow = _now().astimezone(ZoneInfo(timezone)).date() + timedelta(days=1)
        ids = [s.id for s, _ in await today_list(engine, user_id, timezone)]
        async with service_session(engine) as session:
            await session.execute(
                update(Suggestion)
                .where(Suggestion.user_id == user_id, Suggestion.id.in_(ids or [uuid.uuid4()]))
                .values(status="snoozed", snoozed_until=tomorrow)
            )
        await wa.send_text(user_id, "Snoozed. I'll bring them back tomorrow.")
    elif button_id == "show_drafts":
        await _show_drafts(engine, router, wa, settings, user_id, timezone)
    elif button_id.startswith("cap_save:") or button_id.startswith("cap_app:"):
        await _capture_button(engine, wa, settings, user_id, timezone, button_id)
    else:
        await wa.send_text(user_id, HELP)


async def _show_drafts(
    engine: AsyncEngine,
    router: AIRouter | None,
    wa: WhatsAppClient,
    settings: Settings,
    user_id: uuid.UUID,
    timezone: str,
) -> None:
    """FR-WA-5: each draft as its own message, so the user can forward or copy it."""
    items = (await today_list(engine, user_id, timezone))[:3]
    if not items:
        await wa.send_text(user_id, "No drafts for today.")
        return
    texts: list[str] = []
    for s, c in items:
        async with service_session(engine) as session:
            draft = await session.scalar(
                select(Draft).where(Draft.suggestion_id == s.id, Draft.user_id == user_id)
            )
            if draft is not None:
                texts.append(draft.final_text or draft.text)
                continue
            now = _now()
            plan = await billing.current_plan(session, user_id, now)
            used = await billing.drafts_this_month(session, user_id, now, timezone)
            if (
                router is None
                or not can_create_draft(plan, used, billing.limits_from(settings)).allowed
            ):
                break
            ctx = await load_context(session, user_id, c, s.stage)
        try:
            gen = await generate(router, ctx, None, user_id, variation=False)
        except AIUnavailableError:
            break
        async with service_session(engine) as session:
            session.add(
                Draft(
                    user_id=user_id,
                    suggestion_id=s.id,
                    contact_id=c.id,
                    stage=s.stage,
                    language=ctx.profile.language,
                    provider=gen.provider,
                    model=gen.model,
                    prompt_version=gen.prompt_version,
                    text=gen.text,
                    factcheck={"unsupported": gen.unsupported, "warnings": gen.warnings},
                )
            )
            await session.execute(
                update(Suggestion)
                .where(Suggestion.id == s.id, Suggestion.user_id == user_id)
                .values(status="opened")
            )
        texts.append(gen.text)
    if not texts:
        await wa.send_text(
            user_id, f"Open the app to write today's drafts: {settings.app_base_url}/today"
        )
        return
    await wa.send_text(
        user_id, "Here are today's drafts. Forward each one to the person, or copy it."
    )
    for text in texts:
        await wa.send_text(user_id, text)
    await wa.send_text(
        user_id,
        "After you send them, tap Sent? in the app so your progress stays right: "
        f"{settings.app_base_url}/today",
    )


async def _capture(
    engine: AsyncEngine,
    router: AIRouter | None,
    wa: WhatsAppClient,
    settings: Settings,
    user_id: uuid.UUID,
    text: str,
    language: str | None,
    source: str,
) -> None:
    if router is None:
        return
    async with service_session(engine) as session:
        capture = Capture(
            user_id=user_id,
            source=source,
            transcript=text[:4000],
            language=language,
            status="queued",
        )
        session.add(capture)
        await session.flush()
        capture_id = capture.id
    await captures.process_capture(engine, router, Storage(settings), capture_id)
    async with service_session(engine) as session:
        stored = await session.get(Capture, capture_id)
        out = captures.capture_out(stored) if stored is not None else None
    if out is None or out.status != "ready" or not out.people:
        await wa.send_text(
            user_id, "I couldn't find anyone in that note. Try again with names, or open the app."
        )
        return
    lines = []
    for p in out.people:
        detail = ", ".join(x for x in [p.title, p.company] if x)
        extra = f" — follow up {p.follow_up_date:%a %d %b}" if p.follow_up_date else ""
        maybe = f" (is this {p.matches[0].full_name}?)" if p.matches else ""
        lines.append(f"• {p.full_name}{f' ({detail})' if detail else ''}{maybe}{extra}")
    n = len(out.people)
    await wa.send_buttons(
        user_id,
        f"Found {n} {'person' if n == 1 else 'people'}:\n" + "\n".join(lines),
        [(f"cap_save:{capture_id}", "Save"), (f"cap_app:{capture_id}", "Edit in app")],
    )


async def _voice(
    engine: AsyncEngine,
    router: AIRouter | None,
    wa: WhatsAppClient,
    settings: Settings,
    user_id: uuid.UUID,
    msg: Inbound,
) -> None:
    async with service_session(engine) as session:
        allowed = await has_consent(session, user_id, "voice")
    if not allowed:
        await wa.send_text(
            user_id,
            "Allow voice processing in the app to send voice notes: "
            f"{settings.app_base_url}/settings",
        )
        return
    if router is None or msg.media_id is None:
        return
    try:
        audio, mime = await wa.download_media(msg.media_id, MAX_AUDIO_BYTES)
        transcript = await router.transcribe(audio, mime, user_id=user_id, language_hint=None)
    except (WhatsAppError, AIUnavailableError):
        await wa.send_text(user_id, "I couldn't hear that one. Please try again, or type it.")
        return
    finally:
        audio = b""  # never kept: the audio lives only in memory for transcription
    await _capture(
        engine, router, wa, settings, user_id, transcript.text, transcript.language, "wa_audio"
    )


async def _capture_button(
    engine: AsyncEngine,
    wa: WhatsAppClient,
    settings: Settings,
    user_id: uuid.UUID,
    timezone: str,
    button_id: str,
) -> None:
    action, _, raw_id = button_id.partition(":")
    try:
        capture_id = uuid.UUID(raw_id)
    except ValueError:
        return
    link = f"{settings.app_base_url}/capture?id={capture_id}"
    if action == "cap_app":
        await wa.send_text(user_id, f"Review and edit them here: {link}")
        return
    async with service_session(engine) as session:
        capture = await session.scalar(
            select(Capture).where(Capture.id == capture_id, Capture.user_id == user_id)
        )
        if capture is None or capture.status != "ready":
            await wa.send_text(user_id, "That note was already handled.")
            return
        people = (capture.extracted or {}).get("people", [])
        if any(p.get("matches") for p in people):
            await wa.send_text(
                user_id, f"Some of them might already be in your people. Please check here: {link}"
            )
            return
        now = _now()
        plan = await billing.current_plan(session, user_id, now)
        result = await captures.confirm(
            session,
            user_id,
            capture,
            CaptureConfirm(decisions=[CaptureDecision(key=p["key"], action="new") for p in people]),
            now.astimezone(ZoneInfo(timezone)).date(),
            plan.kind,
        )
    extra = (
        f" and added {result.follow_ups} follow-up{'s' if result.follow_ups != 1 else ''} to Today"
        if result.follow_ups
        else ""
    )
    await wa.send_text(user_id, f"Saved {result.created} to your people{extra}.")


async def _contacts(
    engine: AsyncEngine,
    wa: WhatsAppClient,
    user_id: uuid.UUID,
    timezone: str,
    shared: list[SharedContact],
) -> None:
    async with service_session(engine) as session:
        if not await has_consent(session, user_id, "contacts"):
            await wa.send_text(
                user_id, "Allow contact import in the app first, then share the contact again."
            )
            return
        parsed = parse_picker(
            [{"name": [c.name], "tel": c.phones, "email": c.emails} for c in shared]
        )
        job = await stage_import(session, user_id, "picker", parsed)
        job = await commit_import(
            session, user_id, job, _now().astimezone(ZoneInfo(timezone)).date()
        )
        new, merged = job.counts.get("new", 0), job.counts.get("merged", 0)
    await wa.send_text(
        user_id, f"Added {new} new, updated {merged}. Add a note about them anytime."
    )


async def send_daily_briefs(engine: AsyncEngine, wa: WhatsAppClient, settings: Settings) -> int:
    """FR-WA-4: paying, opted-in users at their nudge time; once per local day; templates only."""
    if not settings.wa_briefs_enabled:
        return 0
    now = _now()
    async with service_session(engine) as session:
        profiles = list(
            await session.scalars(
                select(Profile).where(
                    Profile.wa_phone_e164.is_not(None),
                    Profile.wa_opt_in_at.is_not(None),
                    Profile.wa_opt_out_at.is_(None),
                )
            )
        )
    sent = 0
    for p in profiles:
        local = now.astimezone(ZoneInfo(p.timezone))
        nudge = datetime.combine(local.date(), p.nudge_time, tzinfo=local.tzinfo)
        if not (nudge <= local < nudge + timedelta(minutes=15)):
            continue
        day_start = datetime.combine(local.date(), time.min, tzinfo=local.tzinfo)
        async with service_session(engine) as session:
            plan = await billing.current_plan(session, p.user_id, now)
            if plan.kind == "free":
                continue  # rule 5: no WhatsApp messages initiated by us for free users
            already = await session.scalar(
                select(WaMessage.id).where(
                    WaMessage.user_id == p.user_id,
                    WaMessage.template_name == DAILY_BRIEF,
                    WaMessage.created_at >= day_start,
                )
            )
        if already is not None:
            continue
        items = await today_list(engine, p.user_id, p.timezone)
        if not items:
            continue
        params = brief_params(
            (p.display_name or "").split(" ")[0], [_line(s, c) for s, c in items[:3]]
        )
        try:
            await wa.send_template(p.user_id, DAILY_BRIEF, params, ["show_drafts", "snooze_today"])
            sent += 1
        except (RecipientNotAllowedError, WhatsAppError) as exc:
            logger.warning("wa_brief_failed", extra={"error_type": type(exc).__name__})
    return sent
