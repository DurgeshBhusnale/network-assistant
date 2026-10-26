"""Profile lookup/creation inside a user (RLS) session."""

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.auth import AuthUser
from app.core.config import Settings
from app.core.errors import AppError, ErrorCode
from app.domain.models import Profile
from app.domain.schemas import ProfileOut


async def ensure_profile(session: AsyncSession, user: AuthUser) -> Profile:
    """The profile row is created on the user's first authenticated request."""
    try:
        async with session.begin_nested():
            await session.execute(
                insert(Profile)
                .values(user_id=user.id)
                .on_conflict_do_nothing(index_elements=["user_id"])
            )
    except IntegrityError as exc:
        # A still-valid token for an account that was deleted.
        raise AppError(ErrorCode.UNAUTHENTICATED, "This account no longer exists.", 401) from exc
    profile = await session.scalar(select(Profile).where(Profile.user_id == user.id))
    assert profile is not None
    return profile


def profile_out(profile: Profile, user: AuthUser, settings: Settings) -> ProfileOut:
    return ProfileOut(
        user_id=profile.user_id,
        email=user.email,
        display_name=profile.display_name,
        language=profile.language,
        timezone=profile.timezone,
        nudge_time=profile.nudge_time.strftime("%H:%M"),
        onboarding_step=profile.onboarding_step,
        privacy_notice_accepted=profile.privacy_notice_version == settings.privacy_notice_version,
        whatsapp_linked=profile.wa_phone_e164 is not None,
        email_digest=profile.email_digest,
    )
