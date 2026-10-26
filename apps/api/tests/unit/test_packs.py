import copy
from typing import Any

import pytest
from pydantic import ValidationError

from app.core.config import REPO_ROOT
from app.db_seed import load_pack_rows, render_seed
from app.engine.packs import Pack, PackSummary, UnknownOutcomeError, UnknownStageError, parse_pack


@pytest.mark.parametrize("fixture", ["career_sprint_config", "freelance_test_config"])
def test_active_packs_parse_as_full_engine_config(fixture: str, request: Any) -> None:
    pack = parse_pack(request.getfixturevalue(fixture))
    assert isinstance(pack, Pack)


def test_career_sprint_stages_and_outcomes(career_sprint_config: dict[str, Any]) -> None:
    pack = Pack.model_validate(career_sprint_config)

    assert [s.id for s in pack.stages] == ["warm_up", "ask", "follow_up", "thank"]
    assert pack.stage("ask").has_ask is True
    assert pack.stage("warm_up").has_ask is False
    assert pack.validate_outcome("referred") == "referred"
    assert pack.copy_.picker_label == "Get referred"


def test_second_pack_uses_its_own_vocabulary(freelance_test_config: dict[str, Any]) -> None:
    pack = Pack.model_validate(freelance_test_config)

    assert pack.stage("pitch").has_ask is True
    assert pack.validate_outcome("client_won") == "client_won"
    with pytest.raises(UnknownStageError):
        pack.stage("ask")
    with pytest.raises(UnknownOutcomeError):
        pack.validate_outcome("referred")


def test_unknown_stage_and_outcome_rejected(career_sprint_config: dict[str, Any]) -> None:
    pack = Pack.model_validate(career_sprint_config)
    with pytest.raises(UnknownStageError):
        pack.stage("pitch")
    with pytest.raises(UnknownOutcomeError):
        pack.validate_outcome("client_won")


def _broken(config: dict[str, Any], **changes: Any) -> dict[str, Any]:
    data = copy.deepcopy(config)
    data.update(changes)
    return data


@pytest.mark.parametrize(
    "changes",
    [
        {"stages": []},
        {"outcomes": ["won"]},
        {"success_metric": {"outcome": "hired", "target_param": "x"}},
        {"daily_list": {"min": 5, "max": 7, "default": 3, "max_per_company": 2}},
        {"copy": {}},
        {"id": "Career Sprint"},
    ],
)
def test_invalid_pack_configs_rejected(
    career_sprint_config: dict[str, Any], changes: dict[str, Any]
) -> None:
    with pytest.raises(ValidationError):
        Pack.model_validate(_broken(career_sprint_config, **changes))


def test_duplicate_stage_ids_rejected(career_sprint_config: dict[str, Any]) -> None:
    stages = career_sprint_config["stages"]
    with pytest.raises(ValidationError):
        Pack.model_validate(_broken(career_sprint_config, stages=[*stages, stages[0]]))


def test_pack_with_only_ask_stages_rejected(career_sprint_config: dict[str, Any]) -> None:
    only_ask = [s for s in career_sprint_config["stages"] if s["has_ask"]]
    with pytest.raises(ValidationError):
        Pack.model_validate(_broken(career_sprint_config, stages=only_ask))


def test_coming_soon_packs_need_only_a_summary() -> None:
    rows = load_pack_rows()

    assert [r["id"] for r in rows] == [
        "career_sprint",
        "freelance_clients",
        "fundraising",
        "partners_hires_vendors",
    ]
    for row in rows[1:]:
        summary = parse_pack(row)
        assert type(summary) is PackSummary
        assert summary.status == "coming_soon"
        assert summary.copy_.picker_label


def test_seed_in_sync_with_packs() -> None:
    seed = (REPO_ROOT / "supabase" / "seed.sql").read_text(encoding="utf-8")
    assert seed == render_seed(), "run `uv run python -m app.db_seed`"
