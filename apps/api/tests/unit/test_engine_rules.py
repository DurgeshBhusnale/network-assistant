from datetime import date
from typing import Any

import pytest

from app.billing.limits import (
    Decision,
    LimitCode,
    Limits,
    Plan,
    can_create_draft,
    can_regenerate,
    regenerations_left,
)
from app.engine.capture import (
    ExtractedPerson,
    ExtractResult,
    KnownContact,
    build_candidates,
    matches_for,
    memory_texts,
    valid_follow_up,
)
from app.engine.drafting import MAX_WORDS, check_rules, job_link_for
from app.engine.goals import GoalParamsError, goal_end_date, validate_goal_params
from app.engine.packs import Pack
from app.engine.relevance import UNLABELLED_WEIGHT, deterministic_label, matching_target, weight
from app.engine.send import edit_ratio, whatsapp_url

LIMITS = Limits(free_drafts_per_month=3, free_regenerations_per_draft=3, sprint_fair_use_drafts=400)


@pytest.fixture
def pack(career_sprint_config: dict[str, Any]) -> Pack:
    return Pack.model_validate(career_sprint_config)


# --- billing/limits.py: the single plan gate -------------------------------------------------


@pytest.mark.parametrize(
    ("plan", "used", "expected"),
    [
        (Plan("free"), 0, Decision(True, None, 2)),
        (Plan("free"), 2, Decision(True, None, 0)),
        (Plan("free"), 3, Decision(False, LimitCode.FREE_LIMIT_REACHED, 0)),
        (Plan("free"), 9, Decision(False, LimitCode.FREE_LIMIT_REACHED, 0)),
        (Plan("sprint", drafts_used=399), 99, Decision(True)),
        (Plan("sprint", drafts_used=400), 0, Decision(False, LimitCode.FAIR_USE_REACHED, 0)),
        (Plan("pro", drafts_used=10_000), 99, Decision(True)),
    ],
)
def test_can_create_draft(plan: Plan, used: int, expected: Decision) -> None:
    assert can_create_draft(plan, used, LIMITS) == expected


@pytest.mark.parametrize(
    ("plan", "so_far", "allowed", "left"),
    [
        (Plan("free"), 0, True, 3),
        (Plan("free"), 2, True, 1),
        (Plan("free"), 3, False, 0),
        (Plan("free"), 5, False, 0),
        (Plan("sprint"), 50, True, None),
    ],
)
def test_regenerations(plan: Plan, so_far: int, allowed: bool, left: int | None) -> None:
    decision = can_regenerate(plan, so_far, LIMITS)
    assert decision.allowed is allowed
    if not allowed:
        assert decision.code == LimitCode.FREE_REGEN_LIMIT_REACHED
    assert regenerations_left(plan, so_far, LIMITS) == left


# --- engine/send.py: the user sends, from their own WhatsApp ---------------------------------


def test_whatsapp_url_uses_digits_and_encodes_text() -> None:
    url = whatsapp_url("+91 98765 43210", "Hi Priya! Kaise ho? 50% & more #1")
    assert (
        url
        == "https://wa.me/919876543210?text=Hi%20Priya%21%20Kaise%20ho%3F%2050%25%20%26%20more%20%231"
    )


@pytest.mark.parametrize(
    ("generated", "final", "expected"),
    [("hello", None, 0.0), ("hello", "hello", 0.0), ("abcd", "abce", 0.25), ("ab", "xy", 1.0)],
)
def test_edit_ratio(generated: str, final: str | None, expected: float) -> None:
    assert edit_ratio(generated, final) == expected


# --- engine/drafting.py: honest drafts, warm-ups without an ask ------------------------------


@pytest.mark.parametrize(
    ("text", "has_ask", "warnings"),
    [
        ("Hey Priya, saw your talk at eChai. Loved it!", False, []),
        ("Hey Priya, could you refer me for the backend role?", False, ["contains_ask"]),
        ("Hey Priya, could you refer me for the backend role?", True, []),
        ("Bhai, referral mil sakta hai? Job ke liye pooch raha tha", False, ["contains_ask"]),
        ("Here is my resume", False, ["contains_ask"]),
        ("word " * (MAX_WORDS + 1), True, ["too_long"]),
        ("Check https://evil.example/x.", True, ["unexpected_link"]),
        ("Role: https://careers.zoho.com/jobs/1", True, []),  # the goal's own job link
        ("Hey Priya, कैसे हो?", True, ["wrong_script"]),
    ],
)
def test_check_rules(text: str, has_ask: bool, warnings: list[str]) -> None:
    result = check_rules(
        text, stage_has_ask=has_ask, allowed_urls=["https://careers.zoho.com/jobs/1/"]
    )
    assert result.warnings() == warnings
    assert result.ok is (warnings == [])
    assert len(result.fix_instructions()) == len(warnings)


def test_devanagari_is_fine_for_hindi_and_marathi() -> None:
    for language in ("hi", "mr"):
        assert check_rules("नमस्ते प्रिया", stage_has_ask=True, allowed_urls=[], language=language).ok


@pytest.mark.parametrize(
    ("company", "expected"),
    [
        ("zoho", "https://careers.zoho.com/jobs/1"),
        ("razorpay software", "https://razorpay.com/jobs/2"),
        ("ibm", None),  # 3-letter token present nowhere
        (None, None),
    ],
)
def test_job_link_for(company: str | None, expected: str | None) -> None:
    links = ["https://careers.zoho.com/jobs/1", "https://razorpay.com/jobs/2"]
    assert job_link_for(company, links) == expected


# --- engine/relevance.py ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("company", "expected"),
    [
        ("zoho", "target_company"),
        ("zoho corp", "target_company"),  # token set match
        ("razorpay software", "target_company"),
        ("zomato", None),
        (None, None),
    ],
)
def test_deterministic_label(pack: Pack, company: str | None, expected: str | None) -> None:
    assert deterministic_label(pack, company, ["zoho", "razorpay"]) == expected


def test_matching_target_and_weights(pack: Pack) -> None:
    assert matching_target("zoho corp", ["razorpay", "zoho"]) == "zoho"
    assert matching_target("zomato", ["zoho"]) is None
    assert weight(pack, "target_company") == 1.0
    assert weight(pack, "not_relevant") == 0.1
    assert weight(pack, None) == UNLABELLED_WEIGHT
    assert weight(pack, "made_up_label") == UNLABELLED_WEIGHT


# --- engine/goals.py: params validated against the pack's goal_schema ------------------------


def test_goal_params_get_defaults_and_cleaning(pack: Pack) -> None:
    params = validate_goal_params(pack, {"role": "  Backend  ", "companies": ["Zoho", " ", ""]})
    assert params == {
        "role": "Backend",
        "companies": ["Zoho"],
        "referrals_target": 4,
        "locations": [],
        "job_links": [],
    }


@pytest.mark.parametrize(
    ("params", "fields"),
    [
        ({"companies": ["Zoho"]}, ["role"]),
        ({"role": "Backend", "companies": []}, ["companies"]),
        ({"role": "B", "companies": ["Zoho"]}, ["role"]),
        ({"role": "Backend", "companies": ["Zoho"], "referrals_target": 11}, ["referrals_target"]),
        ({"role": "Backend", "companies": ["Zoho"], "job_links": ["ftp://x"]}, ["job_links"]),
        (
            {"role": "Backend", "companies": ["Zoho"], "job_links": ["javascript:alert(1)"]},
            ["job_links"],
        ),
        ({"role": "Backend", "companies": ["Zoho"], "salary": 10}, ["params"]),
        ({"role": "Backend", "companies": [f"C{i}" for i in range(16)]}, ["companies"]),
    ],
)
def test_goal_params_rejected(pack: Pack, params: dict[str, Any], fields: list[str]) -> None:
    with pytest.raises(GoalParamsError) as exc:
        validate_goal_params(pack, params)
    assert exc.value.fields == fields


def test_goal_end_date_is_pack_duration(pack: Pack) -> None:
    assert goal_end_date(pack, date(2026, 10, 25)) == date(2026, 12, 24)


# --- engine/capture.py: candidates for confirm cards, never auto-merged ----------------------

DAY = date(2026, 10, 25)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("2026-10-30", date(2026, 10, 30)),
        ("2026-10-25T10:00:00", DAY),
        ("2026-10-24", None),  # in the past
        ("2027-10-26", None),  # more than a year out
        ("next friday", None),
        (None, None),
    ],
)
def test_valid_follow_up(value: str | None, expected: date | None) -> None:
    assert valid_follow_up(value, DAY) == expected


KNOWN = [
    KnownContact("k1", "Priya Nair", "zoho"),
    KnownContact("k2", "Priya Sharma", "razorpay"),
    KnownContact("k3", "Arjun Mehta", None),
]


def test_matches_for_uses_name_and_company() -> None:
    assert matches_for("Priya Nair", "zoho", KNOWN)[0] == {
        "contact_id": "k1",
        "full_name": "Priya Nair",
        "score": 100,
    }
    # Same name, different company: still suggested (people change jobs), but scored lower.
    assert [(m["contact_id"], m["score"]) for m in matches_for("Priya Nair", "infosys", KNOWN)] == [
        ("k1", 85)
    ]
    # A near name at a different company is not.
    assert matches_for("Priya Nayar", "infosys", KNOWN) == []
    assert [m["contact_id"] for m in matches_for("Arjun Mehta", "flipkart", KNOWN)] == ["k3"]
    assert matches_for("Someone Else", None, KNOWN) == []


def test_build_candidates_cleans_and_drops_nameless() -> None:
    result = ExtractResult(
        people=[
            ExtractedPerson(
                first_name="priya",
                last_name="nair",
                company="Zoho Corp",
                where_met="eChai Pune",
                facts=["Likes AI agents", "Likes AI agents", "  "],
                commitments=["send my resume"],
                follow_up_date="2026-11-01",
            ),
            ExtractedPerson(first_name="  "),
        ],
        unassigned_facts=["Event was crowded"],
    )
    out = build_candidates(result, KNOWN, DAY)
    assert out["dropped"] == 1
    (p,) = out["people"]
    assert p["full_name"] == "Priya Nair"
    assert p["facts"] == ["Likes AI agents"]
    assert p["follow_up_date"] == "2026-11-01"
    assert [m["contact_id"] for m in p["matches"]] == ["k1"]
    assert memory_texts(p["facts"], p["commitments"], p["where_met"]) == [
        "Met at eChai Pune",
        "Likes AI agents",
        "You promised: send my resume",
    ]


def test_voice_memory_for_one_person_attaches_loose_facts_to_them() -> None:
    priya = KNOWN[0]
    memory = ExtractResult(unassigned_facts=["Moving to Bengaluru"])
    out = build_candidates(memory, KNOWN, DAY, priya)
    (p,) = out["people"]
    assert p["facts"] == ["Moving to Bengaluru"]
    assert p["matches"] == [{"contact_id": "k1", "full_name": "Priya Nair", "score": 100}]
