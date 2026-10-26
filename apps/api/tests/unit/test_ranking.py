from datetime import date, timedelta
from typing import Any

import pytest

from app.engine.packs import Pack
from app.engine.ranking import (
    Scored,
    Signals,
    ease,
    fatigue,
    next_stage,
    reasons,
    score,
    select,
    timing,
    warmth,
)

TODAY = date(2026, 10, 25)


def ago(days: int) -> date:
    return TODAY - timedelta(days=days)


@pytest.fixture
def pack(career_sprint_config: dict[str, Any]) -> Pack:
    return Pack.model_validate(career_sprint_config)


def sig(**kw: Any) -> Signals:
    base: dict[str, Any] = {
        "contact_id": "c1",
        "company_norm": "zoho",
        "has_phone": True,
        "has_linkedin": False,
        "relevance_label": "target_company",
    }
    return Signals(**{**base, **kw})


@pytest.mark.parametrize(
    ("kw", "expected"),
    [
        ({}, 0.2),  # never interacted: floor
        ({"weighted_interactions": 2, "last_interaction": ago(30)}, 0.7),
        ({"weighted_interactions": 2, "last_interaction": ago(200)}, 0.6),
        ({"weighted_interactions": 4, "last_interaction": ago(400)}, 0.8),
        ({"weighted_interactions": 10, "last_interaction": ago(10)}, 1.0),  # capped
    ],
)
def test_warmth(kw: dict[str, Any], expected: float) -> None:
    assert warmth(sig(**kw), TODAY) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("kw", "festival", "expected"),
    [
        ({}, False, 1.0),
        ({"birthday_today": True}, False, 1.5),
        ({"birthday_today": True}, True, 2.25),
        ({"last_met": ago(7)}, False, 1.3),
        ({"last_met": ago(8)}, False, 1.0),
        ({"job_change": ago(30)}, False, 1.2),
        ({"job_change": ago(31)}, False, 1.0),
    ],
)
def test_timing(pack: Pack, kw: dict[str, Any], festival: bool, expected: float) -> None:
    assert timing(sig(**kw), pack, TODAY, festival) == pytest.approx(expected)


@pytest.mark.parametrize(
    ("phone", "linkedin", "expected"),
    [(True, True, 1.0), (True, False, 1.0), (False, True, 0.8), (False, False, 0.5)],
)
def test_ease(phone: bool, linkedin: bool, expected: float) -> None:
    assert ease(sig(has_phone=phone, has_linkedin=linkedin)) == expected


WARM = {"weighted_interactions": 2, "last_interaction": ago(30)}  # warmth 0.7 >= 0.6


@pytest.mark.parametrize(
    ("kw", "expected"),
    [
        ({}, "warm_up"),  # cold: reconnect first, no ask
        (WARM, "ask"),  # warm enough to ask directly
        ({"state": "warmed", "last_reconnect_sent": ago(1)}, None),  # wait 3 days
        ({"state": "warmed", "last_reconnect_sent": ago(3)}, "ask"),
        ({"state": "warmed"}, "ask"),
        ({"state": "replied", "last_reconnect_sent": ago(5)}, "ask"),  # replied to warm-up
        ({"state": "asked", "last_ask_sent": ago(5)}, None),  # waiting for a reply
        ({"state": "asked", "last_ask_sent": ago(40), "last_no_reply": ago(29)}, None),
        ({"state": "asked", "last_ask_sent": ago(40), "last_no_reply": ago(30)}, "follow_up"),
        (
            {
                "state": "asked",
                "last_ask_sent": ago(60),
                "last_no_reply": ago(35),
                "last_follow_up_sent": ago(2),
            },
            None,  # already followed up after the no-reply
        ),
        ({"state": "replied", "last_ask_sent": ago(5), "last_no_reply": ago(40)}, None),
        ({"state": "won"}, "thank"),
        ({"state": "won", "thanked": True}, None),
    ],
)
def test_next_stage(pack: Pack, kw: dict[str, Any], expected: str | None) -> None:
    stage = next_stage(sig(**kw), pack, TODAY)
    assert (stage.id if stage else None) == expected


@pytest.mark.parametrize(
    ("kw", "stage_id", "expected"),
    [
        ({}, "ask", 0.0),
        ({"dismissed": True}, "ask", 1.0),
        ({"dismissed": True}, "thank", 0.0),  # thank-yous skip fatigue
        ({"snoozed_until": TODAY + timedelta(days=1)}, "warm_up", 1.0),
        ({"snoozed_until": TODAY}, "warm_up", 0.0),  # snooze ends today
        ({"last_ask_sent": ago(10)}, "ask", 1.0),  # no second ask within 30 days
        ({"last_ask_sent": ago(30)}, "ask", 0.0),
        ({"last_ask_sent": ago(10)}, "follow_up", 0.0),
        ({"last_sent": ago(3)}, "warm_up", 0.5),
        ({"last_sent": ago(7)}, "warm_up", 0.0),
    ],
)
def test_fatigue(pack: Pack, kw: dict[str, Any], stage_id: str, expected: float) -> None:
    assert fatigue(sig(**kw), pack.stage(stage_id), pack, TODAY) == expected


def test_score_multiplies_the_factors(pack: Pack) -> None:
    s = score(sig(**WARM), pack, TODAY, festival_name=None, deterministic_label="target_company")
    assert s is not None
    assert s.stage.id == "ask"
    assert s.score == pytest.approx(1.0 * 0.7 * 1.0 * 1.0)

    lower = score(
        sig(**WARM, relevance_label=None, has_phone=False, has_linkedin=True),
        pack,
        TODAY,
        festival_name=None,
        deterministic_label=None,
    )
    assert lower is not None
    assert lower.score == pytest.approx(0.3 * 0.7 * 0.8)  # unlabelled weight, LinkedIn only


@pytest.mark.parametrize(
    "kw",
    [
        {"state": "won", "thanked": True},  # nothing left to send
        {"dismissed": True},  # fully fatigued
        {"last_ask_sent": ago(3), **WARM},
    ],
)
def test_score_drops_people_with_nothing_to_send(pack: Pack, kw: dict[str, Any]) -> None:
    assert score(sig(**kw), pack, TODAY, festival_name=None, deterministic_label=None) is None


def test_reasons_are_highlighted_and_capped_at_three(pack: Pack) -> None:
    s = sig(birthday_today=True, last_met=ago(1), last_interaction=ago(1))
    out = reasons(s, pack, TODAY, "Diwali", "target_company")
    assert len(out) == 3
    assert out[0].highlight is True  # deterministic company match
    assert [r.text for r in out[1:]] == ["Birthday today", "Diwali today"]

    quiet = reasons(sig(relevance_label=None, last_interaction=ago(65)), pack, TODAY, None, None)
    assert [r.text for r in quiet] == ["Last spoke 2 months ago"]

    warmed = reasons(
        sig(relevance_label=None, state="warmed", last_reconnect_sent=ago(1)),
        pack,
        TODAY,
        None,
        None,
    )
    assert [r.text for r in warmed] == ["Warmed up yesterday"]


def _scored(pack: Pack, cid: str, value: float) -> Scored:
    return Scored(sig(contact_id=cid), pack.stage("ask"), value)


def test_select_respects_list_size_and_company_cap(pack: Pack) -> None:
    items = [_scored(pack, f"z{i}", 0.9 - i / 100) for i in range(4)] + [
        _scored(pack, f"o{i}", 0.5 - i / 100) for i in range(4)
    ]
    company = {f"z{i}": "zoho" for i in range(4)} | {f"o{i}": f"other{i}" for i in range(4)}
    chosen = [x.signals.contact_id for x in select(items, pack, company_of=company)]
    assert chosen == ["z0", "z1", "o0", "o1", "o2"]  # 5 per day, at most 2 per company


def test_select_counts_items_already_on_todays_list(pack: Pack) -> None:
    items = [_scored(pack, f"z{i}", 0.9) for i in range(3)] + [_scored(pack, "o1", 0.1)]
    company = {"z0": "zoho", "z1": "zoho", "z2": "zoho", "o1": None}
    chosen = select(
        items, pack, company_of=company, already=3, already_companies=["zoho", "zoho", None]
    )
    assert [x.signals.contact_id for x in chosen] == ["o1"]


def test_select_breaks_ties_by_contact_id(pack: Pack) -> None:
    items = [_scored(pack, cid, 0.5) for cid in ("c3", "c1", "c2")]
    chosen = select(items, pack, company_of={})
    assert [x.signals.contact_id for x in chosen] == ["c1", "c2", "c3"]
