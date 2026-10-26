"""Goal params validation and dates. Pure: behaviour comes from the pack config (ADR-0006)."""

import copy
import re
from datetime import date, timedelta
from typing import Any
from urllib.parse import urlparse

from jsonschema import Draft202012Validator, FormatChecker, ValidationError

from app.engine.packs import Pack


class GoalParamsError(ValueError):
    def __init__(self, fields: list[str]) -> None:
        super().__init__("Invalid goal: " + ", ".join(fields))
        self.fields = fields


def _apply_defaults(schema: dict[str, Any], params: dict[str, Any]) -> dict[str, Any]:
    result = copy.deepcopy(params)
    for name, prop in schema.get("properties", {}).items():
        if name not in result and "default" in prop:
            result[name] = copy.deepcopy(prop["default"])
    return result


def _clean(value: Any) -> Any:
    """Trim strings and drop empty strings from lists (chip inputs)."""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return [c for c in (_clean(v) for v in value) if c != ""]
    return value


_FORMATS = FormatChecker()


@_FORMATS.checks("uri")
def _is_web_url(value: object) -> bool:
    if not isinstance(value, str):
        return True
    parsed = urlparse(value)
    return parsed.scheme in ("http", "https") and bool(parsed.netloc)


def _field(error: ValidationError) -> str:
    if error.validator == "required":
        match = re.search(r"'([^']+)'", error.message)
        return match.group(1) if match else "params"
    path = [str(p) for p in error.absolute_path]
    return path[0] if path else "params"


def validate_goal_params(pack: Pack, params: dict[str, Any]) -> dict[str, Any]:
    """Defaults applied, then validated against the pack's goal_schema."""
    schema = pack.goal_schema
    cleaned = _apply_defaults(schema, {k: _clean(v) for k, v in params.items()})
    validator = Draft202012Validator(schema, format_checker=_FORMATS)
    fields = sorted({_field(e) for e in validator.iter_errors(cleaned)})
    if fields:
        raise GoalParamsError(fields)
    return cleaned


def goal_end_date(pack: Pack, starts_on: date) -> date:
    return starts_on + timedelta(days=pack.duration_days)
