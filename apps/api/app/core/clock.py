"""Injectable clock. Production code asks the clock for "now"; tests freeze it."""

from datetime import UTC, date, datetime, timedelta
from typing import Protocol
from zoneinfo import ZoneInfo


class Clock(Protocol):
    def now(self) -> datetime: ...


class SystemClock:
    def now(self) -> datetime:
        return datetime.now(UTC)


class FrozenClock:
    def __init__(self, at: datetime) -> None:
        if at.tzinfo is None:
            raise ValueError("FrozenClock needs a timezone-aware datetime")
        self._at = at.astimezone(UTC)

    def now(self) -> datetime:
        return self._at

    def advance(self, delta: timedelta) -> None:
        self._at += delta


def local_today(clock: Clock, timezone: str) -> date:
    """The user's calendar date right now in their timezone."""
    return clock.now().astimezone(ZoneInfo(timezone)).date()


_system_clock = SystemClock()


def get_clock() -> Clock:
    """FastAPI dependency; override in tests with a FrozenClock."""
    return _system_clock
