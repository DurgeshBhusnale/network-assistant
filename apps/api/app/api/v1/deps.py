"""Shared route dependencies."""

from typing import Annotated

from fastapi import Depends, Request

from app.core.clock import Clock, get_clock
from app.core.config import Settings, get_settings


def app_settings(request: Request) -> Settings:
    """The settings this app was created with (tests and workers can pass their own)."""
    settings: Settings | None = getattr(request.app.state, "settings", None)
    return settings or get_settings()


SettingsDep = Annotated[Settings, Depends(app_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]
