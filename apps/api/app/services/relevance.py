"""LLM relevance labelling (tech spec §7.2 step 2), batched; runs in the worker."""

import json
import uuid

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine

from app.ai.prompts import render
from app.ai.router import AIRouter
from app.core.db import service_session
from app.domain.models import Contact, GoalContact, Memory
from app.engine.relevance import llm_labels, weight
from app.services.loop import active_goal_and_pack
from app.services.ranking import ensure_goal_contacts

BATCH = 50


class _Label(BaseModel):
    id: str
    label: str
    reason: str = ""


class _Labels(BaseModel):
    labels: list[_Label]


async def label_contacts(engine: AsyncEngine, router: AIRouter, user_id: uuid.UUID) -> int:
    """Labels this user's still-unlabelled contacts for their active goal. Returns how many."""
    async with service_session(engine) as session:
        found = await active_goal_and_pack(session, user_id)
        if found is None:
            return 0
        goal, pack = found
        # Goal-contact rows are otherwise created when Today is ranked; right after an import
        # there are none yet, and labelling would find nobody.
        await ensure_goal_contacts(session, user_id, goal, pack)
        contacts = list(
            await session.scalars(
                select(Contact)
                .join(GoalContact, GoalContact.contact_id == Contact.id)
                .where(
                    GoalContact.goal_id == goal.id,
                    GoalContact.user_id == user_id,
                    GoalContact.relevance_label.is_(None),
                    Contact.user_id == user_id,
                    Contact.deleted_at.is_(None),
                )
            )
        )
        notes: dict[uuid.UUID, list[str]] = {}
        if contacts:
            for m in await session.scalars(
                select(Memory)
                .where(Memory.user_id == user_id, Memory.contact_id.in_([c.id for c in contacts]))
                .order_by(Memory.created_at.desc())
            ):
                bucket = notes.setdefault(m.contact_id, [])
                if len(bucket) < 3:
                    bucket.append(m.text)

    allowed = set(llm_labels(pack))
    prompt_version = pack.prompts["relevance"]
    labelled = 0
    for start in range(0, len(contacts), BATCH):
        batch = contacts[start : start + BATCH]
        lines = "\n".join(
            json.dumps(
                {
                    "id": str(c.id),
                    "title": c.title or "",
                    "company": c.company or "",
                    "how_known": c.how_known or "",
                    "notes": notes.get(c.id, []),
                },
                ensure_ascii=False,
            )
            for c in batch
        )
        prompt = render(
            prompt_version,
            role=str(goal.params.get("role", "")),
            companies=", ".join(goal.params.get("companies", [])),
            locations=", ".join(goal.params.get("locations", [])),
            contacts=lines,
        )
        out, _ = await router.complete_json(
            "label_relevance", prompt_version, prompt, _Labels, user_id=user_id, temperature=0.0
        )
        ids = {str(c.id) for c in batch}
        async with service_session(engine) as session:
            for item in out.labels:
                if item.id not in ids or item.label not in allowed:
                    continue
                gc = await session.scalar(
                    select(GoalContact).where(
                        GoalContact.goal_id == goal.id,
                        GoalContact.user_id == user_id,
                        GoalContact.contact_id == uuid.UUID(item.id),
                        GoalContact.relevance_label.is_(None),
                    )
                )
                if gc is not None:
                    gc.relevance_label = item.label
                    gc.relevance = weight(pack, item.label)
                    gc.relevance_reason = item.reason[:120]
                    labelled += 1
    return labelled
