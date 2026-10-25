from datetime import UTC, date, datetime, timedelta
from typing import Any

import pytest

from app.core.clock import FrozenClock, local_today
from app.core.config import Settings
from app.core.redaction import FIELD_MASK
from app.core.sentry import init_sentry, scrub_event


def test_frozen_clock_and_local_today_across_midnight() -> None:
    # 19:00 UTC on 25 Oct is 00:30 on 26 Oct in India.
    clock = FrozenClock(datetime(2026, 10, 25, 19, 0, tzinfo=UTC))

    assert local_today(clock, "Asia/Kolkata") == date(2026, 10, 26)
    assert local_today(clock, "Europe/London") == date(2026, 10, 25)

    clock.advance(timedelta(days=1))
    assert local_today(clock, "Asia/Kolkata") == date(2026, 10, 27)


def test_frozen_clock_rejects_naive_datetimes() -> None:
    with pytest.raises(ValueError):
        FrozenClock(datetime(2026, 10, 25))


def test_sentry_is_a_noop_without_dsn() -> None:
    assert init_sentry(Settings(sentry_dsn=None)) is False


def test_sentry_scrub_drops_bodies_and_auth_and_redacts_text() -> None:
    event: dict[str, Any] = {
        "message": "failed for rohan@example.com",
        "exception": {"values": [{"type": "ValueError", "value": "bad number 9876543210"}]},
        "request": {
            "url": "http://api/v1/contacts",
            "data": {"full_name": "Priya"},
            "cookies": {"sb": "x"},
            "query_string": "q=priya",
            "headers": {"Authorization": "Bearer t", "User-Agent": "ua"},
        },
    }

    scrubbed = scrub_event(event, {})

    assert scrubbed["message"] == FIELD_MASK
    assert scrubbed["exception"]["values"][0]["value"] == "bad number [phone]"
    assert scrubbed["request"] == {"url": "http://api/v1/contacts", "headers": {"User-Agent": "ua"}}


@pytest.mark.parametrize(
    "url",
    [
        "postgresql://u:p@host:5432/postgres",
        "postgres://u:p@host:5432/postgres",
        "postgresql+asyncpg://u:p@host:5432/postgres",
    ],
)
def test_database_url_always_uses_asyncpg(url: str) -> None:
    assert Settings(database_url=url).database_url == "postgresql+asyncpg://u:p@host:5432/postgres"
