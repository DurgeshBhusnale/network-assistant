"""Ranking, stages and daily selection (tech spec §7.3). Pure, pack-driven (ADR-0006/0008).

score = R * W * T * E * (1 - F)
"""

from dataclasses import dataclass, field
from datetime import date

from app.engine.packs import Pack, Stage
from app.engine.relevance import weight


@dataclass
class Signals:
    """Everything the engine needs about one contact, gathered by the caller."""

    contact_id: str
    company_norm: str | None
    has_phone: bool
    has_linkedin: bool
    relevance_label: str | None
    state: str = "none"  # none | warmed | asked | replied | won
    thanked: bool = False
    weighted_interactions: int = 0  # met and replied count double
    last_interaction: date | None = None
    last_sent: date | None = None
    last_reconnect_sent: date | None = None
    last_ask_sent: date | None = None
    last_follow_up_sent: date | None = None
    last_no_reply: date | None = None
    last_met: date | None = None
    birthday_today: bool = False
    job_change: date | None = None
    snoozed_until: date | None = None
    dismissed: bool = False


@dataclass(frozen=True)
class Reason:
    text: str
    highlight: bool = False


@dataclass
class Scored:
    signals: Signals
    stage: Stage
    score: float
    reasons: list[Reason] = field(default_factory=list)


def _days(today: date, then: date | None) -> int | None:
    return None if then is None else (today - then).days


def warmth(s: Signals, today: date) -> float:
    days = _days(today, s.last_interaction)
    recency = 0.0 if days is None else 0.2 if days < 90 else 0.1 if days < 365 else 0.0
    return max(0.2, min(1.0, 0.2 + 0.15 * min(s.weighted_interactions, 4) + recency))


def timing(s: Signals, pack: Pack, today: date, festival_today: bool) -> float:
    boosts = pack.timing_boosts
    t = 1.0
    if s.birthday_today:
        t *= boosts.get("birthday", 1.0)
    if festival_today:
        t *= boosts.get("festival", 1.0)
    met_days = _days(today, s.last_met)
    if met_days is not None and met_days <= boosts.get("met_recently_days", 7):
        t *= boosts.get("met_recently", 1.0)
    job_days = _days(today, s.job_change)
    if job_days is not None and job_days <= boosts.get("job_change_days", 30):
        t *= boosts.get("job_change", 1.0)
    return t


def ease(s: Signals) -> float:
    return 1.0 if s.has_phone else 0.8 if s.has_linkedin else 0.5


def next_stage(s: Signals, pack: Pack, today: date) -> Stage | None:
    """The stage machine (generic over pack stage roles)."""
    ask = pack.stage_for("ask")
    reconnect = pack.stage_for("reconnect")
    thank = pack.stage_for("thank")
    follow_up = pack.by_role("follow_up")

    if s.state == "won":
        return None if s.thanked else thank
    if s.state in ("asked", "replied") and s.last_ask_sent is not None:
        if follow_up is None or s.last_no_reply is None or s.state == "replied":
            return None
        wait = int(
            follow_up.model_extra.get("after_no_reply_days", 30) if follow_up.model_extra else 30
        )
        followed = s.last_follow_up_sent is not None and s.last_follow_up_sent >= s.last_no_reply
        no_reply_days = _days(today, s.last_no_reply) or 0
        return follow_up if not followed and no_reply_days >= wait else None
    if s.state in ("warmed", "replied"):
        min_days = int((ask.model_extra or {}).get("min_days_after_warm_up", 3))
        since = _days(today, s.last_reconnect_sent)
        return ask if since is None or since >= min_days else None
    direct = float((ask.model_extra or {}).get("direct_if_warmth_at_least", 0.6))
    return ask if warmth(s, today) >= direct else reconnect


def fatigue(s: Signals, stage: Stage, pack: Pack, today: date) -> float:
    """Thank-yous skip fatigue (founder's decision); dated follow-ups never reach scoring."""
    if stage.role == "thank":
        return 0.0
    if s.dismissed or (s.snoozed_until is not None and s.snoozed_until > today):
        return 1.0
    f = pack.fatigue
    ask_days = _days(today, s.last_ask_sent)
    if (
        stage.role != "follow_up"
        and ask_days is not None
        and ask_days < f.get("after_ask_days", 30)
    ):
        return 1.0
    sent_days = _days(today, s.last_sent)
    if sent_days is not None and sent_days < f.get("after_any_message_days", 7):
        return f.get("any_message_factor", 0.5)
    return 0.0


def _ago(days: int) -> str:
    if days <= 0:
        return "today"
    if days == 1:
        return "yesterday"
    if days < 30:
        return f"{days} days ago"
    if days < 365:
        months = days // 30
        return f"{months} month{'s' if months > 1 else ''} ago"
    years = days // 365
    return f"{years} year{'s' if years > 1 else ''} ago"


def reasons(
    s: Signals, pack: Pack, today: date, festival_name: str | None, deterministic_label: str | None
) -> list[Reason]:
    copy_reasons: dict[str, str] = pack.copy_.model_dump().get("relevance_reasons", {})
    out: list[Reason] = []
    if s.relevance_label and s.relevance_label in copy_reasons:
        out.append(
            Reason(copy_reasons[s.relevance_label], s.relevance_label == deterministic_label)
        )
    if s.birthday_today:
        out.append(Reason("Birthday today", True))
    if festival_name:
        out.append(Reason(f"{festival_name} today", True))
    met_days = _days(today, s.last_met)
    if met_days is not None and met_days <= pack.timing_boosts.get("met_recently_days", 7):
        out.append(Reason(f"Met {_ago(met_days)}", True))
    job_days = _days(today, s.job_change)
    if job_days is not None and job_days <= pack.timing_boosts.get("job_change_days", 30):
        out.append(Reason("New job", True))
    if s.state == "warmed" and s.last_reconnect_sent is not None:
        out.append(Reason(f"Warmed up {_ago((today - s.last_reconnect_sent).days)}"))
    elif s.last_interaction is not None:
        out.append(Reason(f"Last spoke {_ago((today - s.last_interaction).days)}"))
    return out[:3]


def score(
    s: Signals,
    pack: Pack,
    today: date,
    *,
    festival_name: str | None,
    deterministic_label: str | None,
) -> Scored | None:
    stage = next_stage(s, pack, today)
    if stage is None:
        return None
    value = (
        weight(pack, s.relevance_label)
        * warmth(s, today)
        * timing(s, pack, today, festival_name is not None)
        * ease(s)
        * (1.0 - fatigue(s, stage, pack, today))
    )
    if value <= 0:
        return None
    return Scored(
        s, stage, round(value, 4), reasons(s, pack, today, festival_name, deterministic_label)
    )


def select(
    scored: list[Scored],
    pack: Pack,
    *,
    company_of: dict[str, str | None],
    already: int = 0,
    already_companies: list[str | None] | None = None,
) -> list[Scored]:
    """Top `daily_list.default` (minus forced items already on the list), ≤ max_per_company each."""
    limit = pack.daily_list.default - already
    per_company: dict[str, int] = {}
    for company in already_companies or []:
        if company:
            per_company[company] = per_company.get(company, 0) + 1
    chosen: list[Scored] = []
    for item in sorted(scored, key=lambda x: (-x.score, x.signals.contact_id)):
        if len(chosen) >= limit:
            break
        company = company_of.get(item.signals.contact_id)
        if company and per_company.get(company, 0) >= pack.daily_list.max_per_company:
            continue
        if company:
            per_company[company] = per_company.get(company, 0) + 1
        chosen.append(item)
    return chosen
