"""AI_MODE switch: picks the provider set for the router."""

from dataclasses import dataclass

from app.ai.base import LLMProvider, STTProvider
from app.ai.providers.fake import FakeProvider
from app.core.config import Settings


class LiveProvidersUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class Providers:
    llm: dict[str, LLMProvider]
    stt: dict[str, STTProvider]


def build_providers(settings: Settings) -> Providers:
    if settings.ai_mode == "fake":
        fake = FakeProvider()
        return Providers(llm={fake.name: fake}, stt={fake.name: fake})
    raise LiveProvidersUnavailableError(
        "AI_MODE=live is not available yet (live providers arrive in Sprint 3); use AI_MODE=fake"
    )
