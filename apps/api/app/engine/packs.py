"""Goal pack configuration (ADR-0006, ADR-0008). Pure: no I/O.

The engine reads all pack behaviour from this model. Stage ids and outcomes are pack data,
stored as text in the database and validated here.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

# Generic per-(goal, contact) states shared by every pack; the DB enforces these.
GOAL_CONTACT_STATES = ("none", "warmed", "asked", "replied", "won")


class UnknownStageError(ValueError):
    pass


class UnknownOutcomeError(ValueError):
    pass


class _Model(BaseModel):
    model_config = ConfigDict(extra="allow", frozen=True)


class Stage(_Model):
    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    label: str
    has_ask: bool
    step: int = Field(ge=1)


class PackCopy(_Model):
    picker_label: str = Field(min_length=1)


class DailyList(_Model):
    min: int = Field(ge=1)
    max: int = Field(ge=1)
    default: int = Field(ge=1)
    max_per_company: int = Field(ge=1)

    @model_validator(mode="after")
    def _ordered(self) -> "DailyList":
        if not self.min <= self.default <= self.max:
            raise ValueError("daily_list must satisfy min <= default <= max")
        return self


class SuccessMetric(_Model):
    outcome: str
    target_param: str


class PackSummary(_Model):
    """Fields every pack has, including coming-soon ones."""

    id: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    name: str = Field(min_length=1)
    status: Literal["active", "coming_soon", "retired"]
    sort_order: int
    copy_: PackCopy = Field(alias="copy")


class Pack(PackSummary):
    """A pack the engine can run."""

    duration_days: int = Field(gt=0)
    goal_schema: dict[str, Any]
    relevance: dict[str, Any]
    stages: tuple[Stage, ...] = Field(min_length=1)
    outcomes: tuple[str, ...] = Field(min_length=1)
    success_metric: SuccessMetric
    timing_boosts: dict[str, float]
    fatigue: dict[str, float]
    daily_list: DailyList
    reply_check_in: dict[str, int]
    prompts: dict[str, str]

    @model_validator(mode="after")
    def _consistent(self) -> "Pack":
        ids = [s.id for s in self.stages]
        if len(ids) != len(set(ids)):
            raise ValueError("stage ids must be unique")
        if len(self.outcomes) != len(set(self.outcomes)):
            raise ValueError("outcomes must be unique")
        if overlap := set(self.outcomes) & set(GOAL_CONTACT_STATES):
            raise ValueError(f"outcomes must not reuse generic states: {sorted(overlap)}")
        if self.success_metric.outcome not in self.outcomes:
            raise ValueError("success_metric.outcome must be one of outcomes")
        if not any(not s.has_ask for s in self.stages):
            raise ValueError("a pack needs at least one stage without an ask")
        return self

    def stage(self, stage_id: str) -> Stage:
        for stage in self.stages:
            if stage.id == stage_id:
                return stage
        raise UnknownStageError(f"{stage_id!r} is not a stage of pack {self.id!r}")

    def validate_outcome(self, outcome: str) -> str:
        if outcome not in self.outcomes:
            raise UnknownOutcomeError(f"{outcome!r} is not an outcome of pack {self.id!r}")
        return outcome


def parse_pack(data: dict[str, Any]) -> PackSummary:
    """Active packs must carry a full engine config; coming-soon packs only a summary."""
    if data.get("status") == "active":
        return Pack.model_validate(data)
    return PackSummary.model_validate(data)
