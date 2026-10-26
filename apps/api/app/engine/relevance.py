"""Relevance (tech spec §7.2). Pure. Deterministic company match first; the LLM labels the rest."""

from typing import Any

from rapidfuzz import fuzz

from app.engine.packs import Pack
from app.imports.normalise import normalise_company

UNLABELLED_WEIGHT = 0.3  # until the LLM labels a contact; between "can introduce" and "same field"


def target_norms(pack: Pack, params: dict[str, Any]) -> list[str]:
    """Normalised target companies from goal params (pack param `companies`, if the pack has it)."""
    return [n for n in (normalise_company(c) for c in params.get("companies", [])) if n]


def deterministic_label(pack: Pack, company_norm: str | None, targets: list[str]) -> str | None:
    det = pack.relevance.get("deterministic") or {}
    label = det.get("label")
    threshold = float(det.get("company_match_threshold", 90))
    if not label or not company_norm or not targets:
        return None
    best = max(fuzz.token_set_ratio(company_norm, t) for t in targets)
    return str(label) if best >= threshold else None


def matching_target(
    company_norm: str | None, targets: list[str], threshold: float = 90
) -> str | None:
    if not company_norm:
        return None
    for t in targets:
        if fuzz.token_set_ratio(company_norm, t) >= threshold:
            return t
    return None


def weight(pack: Pack, label: str | None) -> float:
    if label is None:
        return UNLABELLED_WEIGHT
    weights: dict[str, float] = pack.relevance.get("weights", {})
    return float(weights.get(label, UNLABELLED_WEIGHT))


def llm_labels(pack: Pack) -> list[str]:
    return [str(x) for x in pack.relevance.get("llm_labels", [])]
