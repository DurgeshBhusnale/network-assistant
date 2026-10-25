"""Pure helpers for WhatsApp Cloud API webhooks (tech spec §9): signatures, parsing, commands."""

import hashlib
import hmac
import re
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Literal

FREEFORM_WINDOW = timedelta(hours=24)


def signature_valid(raw_body: bytes, header: str | None, app_secret: str) -> bool:
    """X-Hub-Signature-256 = "sha256=" + HMAC-SHA256(raw body, app secret), constant-time."""
    if not header or not app_secret or not header.startswith("sha256="):
        return False
    expected = hmac.new(app_secret.encode(), raw_body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, header.removeprefix("sha256="))


def can_send_freeform(last_inbound_at: datetime | None, now: datetime) -> bool:
    """Free-form messages only inside 24 h of the user's last message; templates otherwise."""
    return last_inbound_at is not None and now - last_inbound_at < FREEFORM_WINDOW


@dataclass(frozen=True)
class SharedContact:
    name: str
    phones: list[str]
    emails: list[str]


@dataclass(frozen=True)
class Inbound:
    id: str
    sender: str  # digits, as Meta sends them (no "+")
    kind: Literal["text", "audio", "button", "contacts", "other"]
    text: str | None = None
    media_id: str | None = None
    mime: str | None = None
    button_id: str | None = None
    contacts: list[SharedContact] = field(default_factory=list)


@dataclass(frozen=True)
class StatusUpdate:
    id: str
    status: str


def parse_webhook(payload: dict[str, Any]) -> tuple[list[Inbound], list[StatusUpdate]]:
    messages: list[Inbound] = []
    statuses: list[StatusUpdate] = []
    for entry in payload.get("entry", []) or []:
        for change in entry.get("changes", []) or []:
            value = change.get("value") or {}
            for m in value.get("messages", []) or []:
                messages.append(_message(m))
            for s in value.get("statuses", []) or []:
                if s.get("id") and s.get("status"):
                    statuses.append(StatusUpdate(id=str(s["id"]), status=str(s["status"])))
    return [m for m in messages if m.id and m.sender], statuses


def _message(m: dict[str, Any]) -> Inbound:
    mid, sender, kind = str(m.get("id", "")), str(m.get("from", "")), m.get("type")
    if kind == "text":
        return Inbound(mid, sender, "text", text=(m.get("text") or {}).get("body", ""))
    if kind in ("audio", "voice"):
        audio = m.get("audio") or m.get("voice") or {}
        return Inbound(mid, sender, "audio", media_id=audio.get("id"), mime=audio.get("mime_type"))
    if kind == "button":
        return Inbound(mid, sender, "button", button_id=(m.get("button") or {}).get("payload"))
    if kind == "interactive":
        inter = m.get("interactive") or {}
        reply = inter.get("button_reply") or inter.get("list_reply") or {}
        return Inbound(mid, sender, "button", button_id=reply.get("id"))
    if kind == "contacts":
        shared = []
        for c in m.get("contacts", []) or []:
            name = (c.get("name") or {}).get("formatted_name") or ""
            phones = [p.get("phone") or p.get("wa_id") or "" for p in c.get("phones", []) or []]
            emails = [e.get("email", "") for e in c.get("emails", []) or []]
            shared.append(SharedContact(name, [p for p in phones if p], [e for e in emails if e]))
        return Inbound(mid, sender, "contacts", contacts=shared)
    return Inbound(mid, sender, "other")


CommandKind = Literal["link", "start", "stop", "help", "today", "none"]
_LINK = re.compile(r"^\s*start\s+([A-Za-z0-9]{6})\s*$", re.IGNORECASE)
_WORDS: dict[str, CommandKind] = {
    "start": "start",
    "stop": "stop",
    "help": "help",
    "today": "today",
}


@dataclass(frozen=True)
class Command:
    kind: CommandKind
    code: str | None = None


def parse_command(text: str | None) -> Command:
    """Exact keywords only (case-insensitive, trimmed). Anything else is a note to capture."""
    if not text:
        return Command("none")
    link = _LINK.match(text)
    if link:
        return Command("link", link.group(1).upper())
    word = text.strip().strip(".!").lower()
    return Command(_WORDS.get(word, "none"))


def e164(sender_digits: str) -> str:
    digits = "".join(ch for ch in sender_digits if ch.isdigit())
    return f"+{digits}"


def brief_params(first_name: str, lines: list[str], max_line: int = 60) -> list[str]:
    """daily_brief_v1 body params: name + exactly 3 lines (Meta forbids newlines in params)."""

    def clip(s: str) -> str:
        s = " ".join(s.split())
        return s if len(s) <= max_line else s[: max_line - 1] + "…"

    padded = [clip(line) for line in lines[:3]] + ["-"] * (3 - min(3, len(lines)))
    return [clip(first_name or "there"), *padded]
