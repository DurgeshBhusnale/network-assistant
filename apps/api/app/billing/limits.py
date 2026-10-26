"""The single gate for plan limits (CLAUDE.md rule 5). Pure: callers supply usage counts."""

from dataclasses import dataclass
from enum import StrEnum
from typing import Literal

PlanKind = Literal["free", "sprint", "pro"]


class LimitCode(StrEnum):
    FREE_LIMIT_REACHED = "FREE_LIMIT_REACHED"
    FREE_REGEN_LIMIT_REACHED = "FREE_REGEN_LIMIT_REACHED"
    FAIR_USE_REACHED = "FAIR_USE_REACHED"


@dataclass(frozen=True)
class Limits:
    free_drafts_per_month: int
    free_regenerations_per_draft: int
    sprint_fair_use_drafts: int


@dataclass(frozen=True)
class Plan:
    kind: PlanKind
    drafts_used: int = 0  # paid entitlement usage, for fair use


@dataclass(frozen=True)
class Decision:
    allowed: bool
    code: LimitCode | None = None
    remaining: int | None = None


def can_create_draft(plan: Plan, drafts_this_month: int, limits: Limits) -> Decision:
    """A new draft (first generation). Tone changes / Another version use can_regenerate."""
    if plan.kind == "free":
        remaining = limits.free_drafts_per_month - drafts_this_month
        if remaining <= 0:
            return Decision(False, LimitCode.FREE_LIMIT_REACHED, 0)
        return Decision(True, None, remaining - 1)
    if plan.kind == "sprint" and plan.drafts_used >= limits.sprint_fair_use_drafts:
        return Decision(False, LimitCode.FAIR_USE_REACHED, 0)
    return Decision(True)


def can_regenerate(plan: Plan, regenerations_so_far: int, limits: Limits) -> Decision:
    if plan.kind == "free":
        remaining = limits.free_regenerations_per_draft - regenerations_so_far
        if remaining <= 0:
            return Decision(False, LimitCode.FREE_REGEN_LIMIT_REACHED, 0)
        return Decision(True, None, remaining - 1)
    return Decision(True)


def regenerations_left(plan: Plan, regenerations_so_far: int, limits: Limits) -> int | None:
    if plan.kind != "free":
        return None
    return max(0, limits.free_regenerations_per_draft - regenerations_so_far)
