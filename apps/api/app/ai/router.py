"""The single entry point for AI (CLAUDE.md rule 9, tech spec §8).

Per call: timeout (in the provider), 1 retry on retryable errors with jitter, then the task's
fallback model; JSON outputs validated with Pydantic with one repair retry; every attempt logged
to `ai_calls` with a cost estimate. Product code never calls providers directly.
"""

import asyncio
import logging
import random
import uuid
from decimal import Decimal
from typing import TypeVar

from pydantic import BaseModel, ValidationError
from sqlalchemy.ext.asyncio import AsyncEngine

from app.ai.base import LLMProvider, LLMRequest, LLMResult, ProviderError, Task
from app.core.config import Settings
from app.core.db import service_session
from app.domain.models import AICall

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)

REPAIR_SUFFIX = (
    "\n\nYour previous reply was not valid JSON for the requested shape. "
    "Return only valid JSON matching the schema, with no other text."
)


class AIUnavailableError(RuntimeError):
    """Every model in the chain failed."""


class DraftOutput(BaseModel):
    message: str
    facts_used: list[str] = []


class FactcheckOutput(BaseModel):
    unsupported: list[str] = []


class StyleOutput(BaseModel):
    summary: str


class AIRouter:
    def __init__(self, settings: Settings, llm: LLMProvider, engine: AsyncEngine | None) -> None:
        self._settings = settings
        self._llm = llm
        self._engine = engine

    def _models(self, task: Task) -> list[str]:
        s = self._settings
        if task == "draft":
            chain = [s.model_draft, s.model_fallback_draft]
        else:
            chain = [s.model_small, s.model_fallback_small]
        return [m for m in dict.fromkeys(chain) if m] or ["fake"]

    def _cost(self, result: LLMResult) -> Decimal | None:
        price = self._settings.ai_price_inr_per_mtok.get(result.model)
        if price is None:
            return None
        cost = (result.tokens_in * price[0] + result.tokens_out * price[1]) / 1_000_000
        return Decimal(str(round(cost, 4)))

    async def _log(
        self,
        user_id: uuid.UUID | None,
        task: Task,
        prompt_version: str,
        model: str,
        result: LLMResult | None,
        ok: bool,
    ) -> None:
        if self._engine is None:
            return
        try:
            async with service_session(self._engine) as session:
                session.add(
                    AICall(
                        user_id=user_id,
                        task=task,
                        provider=result.provider if result else self._llm.name,
                        model=model,
                        prompt_version=prompt_version,
                        tokens_in=result.tokens_in if result else None,
                        tokens_out=result.tokens_out if result else None,
                        cost_inr=self._cost(result) if result else None,
                        latency_ms=result.latency_ms if result else None,
                        ok=ok,
                    )
                )
        except Exception as exc:
            logger.warning("ai_call_log_failed", extra={"error_type": type(exc).__name__})

    async def _attempt(self, request: LLMRequest, user_id: uuid.UUID | None) -> LLMResult:
        """One model: try, retry once on retryable errors."""
        for attempt in range(2):
            try:
                result = await self._llm.complete(request)
            except ProviderError as exc:
                await self._log(
                    user_id, request.task, request.prompt_version, request.model, None, False
                )
                if not exc.retryable or attempt == 1:
                    raise
                await asyncio.sleep(0.3 + random.random() * 0.4)  # noqa: S311 - jitter
                continue
            await self._log(
                user_id, request.task, request.prompt_version, request.model, result, True
            )
            return result
        raise AssertionError("unreachable")

    async def complete_json(
        self,
        task: Task,
        prompt_version: str,
        prompt: str,
        shape: type[T],
        *,
        user_id: uuid.UUID | None,
        temperature: float = 0.3,
    ) -> tuple[T, LLMResult]:
        last_error: Exception | None = None
        for model in self._models(task):
            request = LLMRequest(
                task=task,
                prompt_version=prompt_version,
                model=model,
                prompt=prompt,
                temperature=temperature,
            )
            try:
                result = await self._attempt(request, user_id)
                try:
                    return shape.model_validate_json(result.text), result
                except ValidationError:
                    repair = request.model_copy(update={"prompt": prompt + REPAIR_SUFFIX})
                    result = await self._attempt(repair, user_id)
                    return shape.model_validate_json(result.text), result
            except (ProviderError, ValidationError) as exc:
                last_error = exc
                logger.warning(
                    "ai_model_failed",
                    extra={"task": task, "model": model, "error_type": type(exc).__name__},
                )
        raise AIUnavailableError(task) from last_error
