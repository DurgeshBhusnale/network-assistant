"""GET/PATCH /v1/me — profile (FR-AUTH-3)."""

from fastapi import APIRouter

from app.api.v1.deps import SettingsDep
from app.core.auth import CurrentUser
from app.core.db import Engine, user_session
from app.domain.schemas import ProfileOut, ProfileUpdate
from app.services.profiles import ensure_profile, profile_out

router = APIRouter(tags=["profile"])


@router.get("/me", response_model=ProfileOut)
async def get_me(user: CurrentUser, engine: Engine, settings: SettingsDep) -> ProfileOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        return profile_out(profile, user, settings)


@router.patch("/me", response_model=ProfileOut)
async def update_me(
    body: ProfileUpdate, user: CurrentUser, engine: Engine, settings: SettingsDep
) -> ProfileOut:
    async with user_session(engine, user) as session:
        profile = await ensure_profile(session, user)
        for field, value in body.model_dump(exclude_unset=True).items():
            if value is not None:
                setattr(profile, field, value)
        await session.flush()
        return profile_out(profile, user, settings)
