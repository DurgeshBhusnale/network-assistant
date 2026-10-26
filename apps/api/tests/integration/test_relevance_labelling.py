"""AI relevance labelling must reach freshly imported contacts (found in the live smoke)."""

import json
import re
from typing import Any

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncEngine

from app.services.relevance import label_contacts
from tests.integration.api import ok
from tests.integration.conftest import MakeUser


class StubRouter:
    """Labels every contact it is sent as 'same_field', like a model would."""

    def __init__(self) -> None:
        self.sent: list[str] = []

    async def complete_json(
        self, task: str, version: str, prompt: str, model: type[BaseModel], **_: Any
    ) -> tuple[BaseModel, None]:
        ids = [json.loads(line)["id"] for line in re.findall(r"^\{.*\}$", prompt, re.M)]
        self.sent.extend(ids)
        labels = [{"id": i, "label": "same_field", "reason": "Engineer"} for i in ids]
        return model.model_validate({"labels": labels}), None


async def test_imported_contacts_are_labelled_before_today_is_opened(
    users: MakeUser, api_engine: AsyncEngine
) -> None:
    u = await users()
    await u.onboard(companies=("Razorpay",))
    for name, company in (
        ("Ananya K", "Razorpay"),
        ("Vikram J", "Postman"),
        ("Sneha D", "Freshworks"),
    ):
        await u.contact(name, company=company)

    router = StubRouter()
    labelled = await label_contacts(api_engine, router, u.id)  # type: ignore[arg-type]

    # Razorpay is a target company (labelled without AI); the other two go to the model.
    assert labelled == 2 and len(router.sent) == 2
    async with api_engine.connect() as conn:
        rows = dict(
            (
                await conn.execute(
                    text(
                        "select c.full_name, gc.relevance_label from goal_contacts gc "
                        "join contacts c on c.id = gc.contact_id where gc.user_id = :u"
                    ),
                    {"u": u.id},
                )
            ).all()
        )
    assert rows == {
        "Ananya K": "target_company",
        "Vikram J": "same_field",
        "Sneha D": "same_field",
    }
    # Running again sends nothing: everyone is labelled.
    assert await label_contacts(api_engine, router, u.id) == 0  # type: ignore[arg-type]
    assert ok(await u.get("/v1/today"))["items"]
