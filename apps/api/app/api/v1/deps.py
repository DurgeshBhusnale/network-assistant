"""Shared route dependencies."""

from typing import Annotated

from fastapi import Depends

from app.core.clock import Clock, get_clock
from app.core.config import Settings, get_settings

SettingsDep = Annotated[Settings, Depends(get_settings)]
ClockDep = Annotated[Clock, Depends(get_clock)]
