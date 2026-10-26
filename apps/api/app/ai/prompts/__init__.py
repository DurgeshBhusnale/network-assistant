"""Versioned prompt files: `<name>.v<N>.md` with `{{placeholders}}` (docs/05-AI-PROMPTS-AND-EVALS).

Every value is PII-scrubbed (phones, emails) before it reaches a provider (CLAUDE.md rule 9).
Conditional wording is computed by the caller; templates only substitute.
"""

import re
from functools import lru_cache
from pathlib import Path

from app.core.redaction import redact_text

PROMPTS_DIR = Path(__file__).resolve().parent
_PLACEHOLDER = re.compile(r"\{\{(\w+)\}\}")


class PromptError(KeyError):
    pass


@lru_cache
def _template(prompt_version: str) -> str:
    path = PROMPTS_DIR / f"{prompt_version}.md"
    if not path.is_file():
        raise PromptError(f"Unknown prompt {prompt_version!r}")
    return path.read_text(encoding="utf-8")


def render(prompt_version: str, **values: str) -> str:
    template = _template(prompt_version)
    missing = set(_PLACEHOLDER.findall(template)) - set(values)
    if missing:
        raise PromptError(f"{prompt_version}: missing {sorted(missing)}")
    return _PLACEHOLDER.sub(lambda m: redact_text(values[m.group(1)]), template)
