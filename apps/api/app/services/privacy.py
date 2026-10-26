"""Data rights (FR-PRIV-2/3) and retention (privacy checklist). Service role, scoped by user_id."""

import csv
import hashlib
import io
import json
import logging
import uuid
import zipfile
from datetime import datetime, timedelta
from typing import Any

import httpx
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.core.config import Settings
from app.core.db import service_session
from app.domain.models import AuditLog

logger = logging.getLogger(__name__)

# Every user-owned table and what to leave out of the export (secrets / staging data).
EXPORT_TABLES: dict[str, list[str]] = {
    "profiles": [],
    "goals": [],
    "contacts": [],
    "memories": ["embedding"],
    "goal_contacts": [],
    "suggestions": [],
    "drafts": [],
    "interactions": [],
    "style_profiles": [],
    "triggers": [],
    "imports": ["preview"],
    "captures": [],
    "consents": [],
    "payments": [],
    "entitlements": [],
    "push_subscriptions": ["keys"],
    "wa_messages": [],
    "events": [],
    "ai_calls": [],
}

RETENTION = {
    "contacts_soft_deleted_days": 30,
    "draft_text_days": 180,
    "wa_messages_days": 90,
    "events_days": 395,  # 13 months
}


def _jsonable(value: Any) -> Any:
    if isinstance(value, datetime | uuid.UUID):
        return str(value)
    return value


async def export_zip(engine: AsyncEngine, user_id: uuid.UUID) -> bytes:
    buffer = io.BytesIO()
    async with service_session(engine) as session:
        with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
            for table, omit in EXPORT_TABLES.items():
                rows = (
                    (
                        await session.execute(
                            text(f"select * from public.{table} where user_id = :u"),  # noqa: S608 - fixed names
                            {"u": user_id},
                        )
                    )
                    .mappings()
                    .all()
                )
                data = [{k: _jsonable(v) for k, v in row.items() if k not in omit} for row in rows]
                zf.writestr(
                    f"{table}.json", json.dumps(data, ensure_ascii=False, indent=2, default=str)
                )
                if table == "contacts":
                    out = io.StringIO()
                    fields = [
                        "full_name",
                        "phones",
                        "emails",
                        "linkedin_url",
                        "company",
                        "title",
                        "city",
                        "how_known",
                        "birthday",
                    ]
                    writer = csv.DictWriter(out, fieldnames=fields, extrasaction="ignore")
                    writer.writeheader()
                    for row in data:
                        writer.writerow(
                            {
                                **row,
                                "phones": "; ".join(row.get("phones") or []),
                                "emails": "; ".join(row.get("emails") or []),
                            }
                        )
                    zf.writestr("contacts.csv", out.getvalue())
            zf.writestr(
                "README.txt",
                "Your [App name] data. One JSON file per table; "
                "contacts.csv opens in a spreadsheet.\n",
            )
        session.add(AuditLog(user_ref=str(user_id), action="export", meta={}))
    return buffer.getvalue()


def user_hash(user_id: uuid.UUID) -> str:
    return hashlib.sha256(f"deleted-user:{user_id}".encode()).hexdigest()


async def _delete_storage(settings: Settings, user_id: uuid.UUID) -> None:
    key = (
        settings.supabase_service_role_key.get_secret_value()
        if settings.supabase_service_role_key
        else ""
    )
    headers = {"Authorization": f"Bearer {key}", "apikey": key}
    base = f"{settings.supabase_url}/storage/v1/object"
    async with httpx.AsyncClient(timeout=20) as client:
        listed = await client.post(
            f"{base}/list/{settings.storage_bucket_captures}",
            headers=headers,
            json={"prefix": f"{user_id}/", "limit": 1000},
        )
        if listed.status_code < 300:
            names = [f"{user_id}/{o['name']}" for o in listed.json() if o.get("name")]
            if names:
                await client.request(
                    "DELETE",
                    f"{base}/{settings.storage_bucket_captures}",
                    headers=headers,
                    json={"prefixes": names},
                )


async def delete_account(engine: AsyncEngine, settings: Settings, user_id: uuid.UUID) -> None:
    """Deletes every row (FK cascades from auth.users; payments are kept anonymised for tax),
    stored files and the sign-in itself. Leaves only a hashed audit entry."""
    await _delete_storage(settings, user_id)
    key = (
        settings.supabase_service_role_key.get_secret_value()
        if settings.supabase_service_role_key
        else ""
    )
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.delete(
            f"{settings.supabase_url}/auth/v1/admin/users/{user_id}",
            headers={"Authorization": f"Bearer {key}", "apikey": key},
        )
    if r.status_code >= 300 and r.status_code != 404:
        raise RuntimeError(f"auth delete failed: {r.status_code}")
    async with service_session(engine) as session:
        # Belt and braces: if the auth delete didn't cascade (e.g. local stack differences).
        await session.execute(text("delete from auth.users where id = :u"), {"u": user_id})
        session.add(AuditLog(user_ref=user_hash(user_id), action="delete_account", meta={}))
        await session.execute(
            text(
                "insert into events (user_id, name, props) "
                "values (null, 'account_deleted', '{}'::jsonb)"
            )
        )


async def apply_retention(engine: AsyncEngine, now: datetime) -> dict[str, int]:
    r = RETENTION
    counts: dict[str, int] = {}
    async with service_session(engine) as session:
        statements = {
            "contacts_purged": (
                "delete from contacts where deleted_at < :t",
                now - timedelta(days=r["contacts_soft_deleted_days"]),
            ),
            "draft_texts_cleared": (
                "update drafts set text = '', final_text = null "
                "where created_at < :t and (text <> '' or final_text is not null)",
                now - timedelta(days=r["draft_text_days"]),
            ),
            "wa_messages_deleted": (
                "delete from wa_messages where created_at < :t",
                now - timedelta(days=r["wa_messages_days"]),
            ),
            "events_deleted": (
                "delete from events where occurred_at < :t",
                now - timedelta(days=r["events_days"]),
            ),
            "ai_calls_deleted": (
                "delete from ai_calls where created_at < :t",
                now - timedelta(days=r["events_days"]),
            ),
        }
        for name, (sql, cutoff) in statements.items():
            result = await session.execute(text(sql), {"t": cutoff})
            counts[name] = int(getattr(result, "rowcount", 0) or 0)
    return counts
