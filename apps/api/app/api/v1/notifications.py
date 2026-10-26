"""Web push subscriptions and one-click email unsubscribe (FR-NOT-1/2)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query
from fastapi.responses import HTMLResponse
from sqlalchemy import delete, update
from sqlalchemy.dialects.postgresql import insert

from app.api.v1.deps import SettingsDep
from app.core.auth import CurrentUser
from app.core.db import Engine, service_session, user_session
from app.domain.models import Profile, PushSubscription
from app.domain.schemas import PushConfigOut, PushSubscriptionIn
from app.services.notifications import unsubscribe_valid

router = APIRouter(tags=["notifications"])


@router.get("/push/config", response_model=PushConfigOut)
async def push_config(settings: SettingsDep) -> PushConfigOut:
    return PushConfigOut(public_key=settings.vapid_public_key or None)


@router.post("/push/subscribe", status_code=204)
async def subscribe(body: PushSubscriptionIn, user: CurrentUser, engine: Engine) -> None:
    async with user_session(engine, user) as session:
        await session.execute(
            insert(PushSubscription)
            .values(user_id=user.id, endpoint=body.endpoint, keys=body.keys)
            .on_conflict_do_update(
                index_elements=["endpoint"], set_={"keys": body.keys, "user_id": user.id}
            )
        )


@router.delete("/push/subscribe", status_code=204)
async def unsubscribe_push(body: PushSubscriptionIn, user: CurrentUser, engine: Engine) -> None:
    async with user_session(engine, user) as session:
        await session.execute(
            delete(PushSubscription).where(
                PushSubscription.user_id == user.id, PushSubscription.endpoint == body.endpoint
            )
        )


_PAGE = (
    "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width'>"
    "<body style='font-family:system-ui;padding:24px;max-width:480px;margin:auto'>"
    "<h1 style='font-size:20px'>{title}</h1><p>{body}</p></body>"
)


async def _unsubscribe(engine: Engine, settings: SettingsDep, u: uuid.UUID, t: str) -> HTMLResponse:
    if not unsubscribe_valid(settings, u, t):
        return HTMLResponse(
            _PAGE.format(title="Link not valid", body="Turn off emails in Settings instead."), 400
        )
    async with service_session(engine) as session:
        await session.execute(
            update(Profile).where(Profile.user_id == u).values(email_digest=False)
        )
    return HTMLResponse(
        _PAGE.format(
            title="You're unsubscribed",
            body="No more weekly emails. You can turn them back on in Settings.",
        )
    )


@router.get("/email/unsubscribe", response_class=HTMLResponse)
async def email_unsubscribe(
    engine: Engine,
    settings: SettingsDep,
    u: Annotated[uuid.UUID, Query()],
    t: Annotated[str, Query(max_length=64)],
) -> HTMLResponse:
    """One-click unsubscribe from the weekly email (signed link; no sign-in needed)."""
    return await _unsubscribe(engine, settings, u, t)


@router.post("/email/unsubscribe", response_class=HTMLResponse, include_in_schema=False)
async def email_unsubscribe_one_click(
    engine: Engine,
    settings: SettingsDep,
    u: Annotated[uuid.UUID, Query()],
    t: Annotated[str, Query(max_length=64)],
) -> HTMLResponse:
    """RFC 8058 List-Unsubscribe-Post (mail clients' one-click button)."""
    return await _unsubscribe(engine, settings, u, t)
