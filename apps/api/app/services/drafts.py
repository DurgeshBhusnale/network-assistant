"""Drafting pipeline (FR-DRAFT-1..6, tech spec §8.3).

generate → code rules + fact check → (if anything fails) regenerate once with fixes →
anything still failing is returned as warnings for the UI to highlight.
"""

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from app.ai.prompts import render
from app.ai.router import AIRouter, DraftOutput, FactcheckOutput
from app.core.db import service_session
from app.core.errors import AppError, ErrorCode
from app.domain.models import (
    Contact,
    Draft,
    Entitlement,
    Goal,
    Interaction,
    Memory,
    Profile,
    StyleProfile,
)
from app.domain.models import Pack as PackRow
from app.domain.schemas import DraftOut
from app.engine.drafting import (
    LANGUAGE_LINES,
    TONE_INSTRUCTIONS,
    RuleCheck,
    check_rules,
    job_link_for,
    word_count,
)
from app.engine.packs import Pack, Stage, UnknownStageError, parse_pack

MAX_MEMORIES = 20
MAX_HISTORY = 3
MAX_STYLE_SAMPLES = 3


@dataclass
class DraftContext:
    pack: Pack
    stage: Stage
    goal: Goal
    contact: Contact
    profile: Profile
    memories: list[str]
    history: list[str]
    style_summary: str | None
    style_samples: list[str]
    job_link: str | None

    @property
    def facts(self) -> list[str]:
        c = self.contact
        params = self.goal.params
        facts = [
            f"Recipient name: {c.full_name}",
            *([f"Recipient title: {c.title}"] if c.title else []),
            *([f"Recipient company: {c.company}"] if c.company else []),
            *([f"Recipient city: {c.city}"] if c.city else []),
            *([f"How they know each other: {c.how_known}"] if c.how_known else []),
            *([f"Sender wants a role: {params.get('role')}"] if params.get("role") else []),
            *(
                [f"Sender's target companies: {', '.join(params.get('companies', []))}"]
                if params.get("companies")
                else []
            ),
            *([f"Job link: {self.job_link}"] if self.job_link else []),
            *self.memories,
            *self.history,
        ]
        return facts


async def load_context(
    session: AsyncSession, user_id: uuid.UUID, contact: Contact, stage_id: str
) -> DraftContext:
    goal = await session.scalar(
        select(Goal).where(Goal.user_id == user_id, Goal.status == "active")
    )
    if goal is None:
        raise AppError(
            ErrorCode.NO_ACTIVE_GOAL, "Set a goal first so drafts know what to ask for.", 409
        )
    pack_row = await session.scalar(select(PackRow).where(PackRow.id == goal.pack_id))
    pack = parse_pack(pack_row.config) if pack_row else None
    if not isinstance(pack, Pack):
        raise AppError(ErrorCode.PACK_NOT_AVAILABLE, "That goal isn't available.", 422)
    try:
        stage = pack.stage(stage_id)
    except UnknownStageError as exc:
        raise AppError(ErrorCode.VALIDATION_ERROR, "Check this field: stage", 422) from exc

    profile = await session.scalar(select(Profile).where(Profile.user_id == user_id))
    assert profile is not None
    memories = await session.scalars(
        select(Memory.text)
        .where(Memory.contact_id == contact.id, Memory.user_id == user_id)
        .order_by(Memory.created_at.desc())
        .limit(MAX_MEMORIES)
    )
    interactions = await session.scalars(
        select(Interaction)
        .where(Interaction.contact_id == contact.id, Interaction.user_id == user_id)
        .order_by(Interaction.occurred_at.desc())
        .limit(MAX_HISTORY)
    )
    history = [
        f"{i.type}{f' ({i.stage})' if i.stage else ''}{f' on {i.channel}' if i.channel else ''}"
        f" {i.occurred_at:%d %b %Y}"
        for i in interactions
    ]
    style = await session.scalar(select(StyleProfile).where(StyleProfile.user_id == user_id))
    return DraftContext(
        pack=pack,
        stage=stage,
        goal=goal,
        contact=contact,
        profile=profile,
        memories=list(memories),
        history=history,
        style_summary=style.summary if style else None,
        style_samples=list(style.samples[:MAX_STYLE_SAMPLES]) if style else [],
        job_link=job_link_for(contact.company_norm, list(goal.params.get("job_links", []))),
    )


def _language(ctx: DraftContext, tone: str | None) -> str:
    return "hinglish" if tone == "hinglish" else ctx.profile.language


def _prompt(ctx: DraftContext, tone: str | None, extra_rules: list[str]) -> str:
    params = ctx.goal.params
    companies = ", ".join(params.get("companies", []))
    user_first = (ctx.profile.display_name or "the user").split(" ")[0]
    contact_first = ctx.contact.first_name or ctx.contact.full_name.split(" ")[0]
    return render(
        ctx.pack.prompts["draft"],
        user_first_name=user_first,
        goal_line=f"{user_first} wants a {params.get('role', 'new')} role"
        + (f" at companies like {companies}" if companies else "")
        + ".",
        stage=ctx.stage.id,
        ask_link_line=f" and include this link: {ctx.job_link}" if ctx.job_link else "",
        language_line=LANGUAGE_LINES.get(_language(ctx, tone), "English"),
        tone_line=TONE_INSTRUCTIONS.get(tone or "", "none"),
        style_summary=ctx.style_summary or "friendly, concise, natural Indian English",
        style_samples="\n---\n".join(ctx.style_samples),
        contact_first_name=contact_first,
        extra_rules="\n".join(f"- {r}" for r in extra_rules),
        contact_name=ctx.contact.full_name,
        contact_title=ctx.contact.title or "unknown",
        contact_company=ctx.contact.company or "unknown",
        how_known=ctx.contact.how_known or "unknown",
        memories="\n".join(f"- {m}" for m in ctx.memories) or "none",
        history="\n".join(f"- {h}" for h in ctx.history) or "none",
    )


@dataclass
class Generated:
    text: str
    unsupported: list[str]
    warnings: list[str]
    provider: str
    model: str
    prompt_version: str
    latency_ms: int


async def _factcheck(
    router: AIRouter, ctx: DraftContext, text: str, user_id: uuid.UUID
) -> list[str]:
    prompt = render("factcheck.v1", facts="\n".join(f"- {f}" for f in ctx.facts), message=text)
    out, _ = await router.complete_json(
        "factcheck", "factcheck.v1", prompt, FactcheckOutput, user_id=user_id, temperature=0.0
    )
    return [c for c in out.unsupported if c.strip()]


async def generate(
    router: AIRouter, ctx: DraftContext, tone: str | None, user_id: uuid.UUID, variation: bool
) -> Generated:
    version = ctx.pack.prompts["draft"]
    base_rules = ["Write a fresh version, different from earlier ones."] if variation else []
    allowed_urls = [ctx.job_link] if ctx.job_link else []
    allowed_urls += [u for m in ctx.memories for u in m.split() if u.startswith("http")]

    async def once(extra: list[str]) -> tuple[DraftOutput, RuleCheck, list[str], Any]:
        out, result = await router.complete_json(
            "draft",
            version,
            _prompt(ctx, tone, base_rules + extra),
            DraftOutput,
            user_id=user_id,
            temperature=0.8 if variation else 0.6,
        )
        text = out.message.strip()
        rules = check_rules(
            text,
            stage_has_ask=ctx.stage.has_ask,
            allowed_urls=allowed_urls,
            language=_language(ctx, tone),
        )
        unsupported = await _factcheck(router, ctx, text, user_id)
        return out, rules, unsupported, result

    out, rules, unsupported, result = await once([])
    if not rules.ok or unsupported:
        fixes = rules.fix_instructions() + [
            f"Do not state this unsupported claim: {c}" for c in unsupported
        ]
        out, rules, unsupported, result = await once(fixes)
    return Generated(
        text=out.message.strip(),
        unsupported=unsupported,
        warnings=rules.warnings() + (["unsupported_claims"] if unsupported else []),
        provider=result.provider,
        model=result.model,
        prompt_version=version,
        latency_ms=result.latency_ms,
    )


async def count_paid_draft(engine: AsyncEngine, entitlement_id: uuid.UUID) -> None:
    """Fair-use counter on the paid entitlement (service role: users can only read entitlements)."""
    async with service_session(engine) as session:
        await session.execute(
            update(Entitlement)
            .where(Entitlement.id == entitlement_id)
            .values(drafts_used=Entitlement.drafts_used + 1)
        )


def draft_out(
    draft: Draft,
    pack: Pack,
    *,
    regenerations_left: int | None,
    drafts_left_this_month: int | None,
    reasons: list[str] | None = None,
) -> DraftOut:
    stage = pack.stage(draft.stage)
    fc = draft.factcheck or {}
    return DraftOut(
        id=draft.id,
        contact_id=draft.contact_id,
        stage=draft.stage,
        stage_label=pack.copy_.model_dump()
        .get("stage_descriptions", {})
        .get(draft.stage, stage.label),
        step=stage.step,
        total_steps=max(s.step for s in pack.stages),
        tone=draft.tone,
        language=draft.language,
        text=draft.text,
        final_text=draft.final_text,
        word_count=word_count(draft.final_text or draft.text),
        unsupported_claims=list(fc.get("unsupported", [])),
        warnings=list(fc.get("warnings", [])),
        reasons=reasons or [],
        regenerations=draft.regenerations,
        regenerations_left=regenerations_left,
        drafts_left_this_month=drafts_left_this_month,
        created_at=draft.created_at,
    )
