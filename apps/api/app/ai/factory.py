"""AI_MODE switch: picks the provider for the router (fake in tests/CI; Groq live, ADR-0010)."""

from dataclasses import dataclass

from app.ai.base import LLMProvider, STTProvider
from app.ai.providers.fake import FakeProvider
from app.ai.providers.groq import GroqProvider
from app.core.config import Settings


class LiveProvidersUnavailableError(RuntimeError):
    pass


@dataclass(frozen=True)
class Providers:
    llm: LLMProvider
    stt: STTProvider


def build_providers(settings: Settings) -> Providers:
    if settings.ai_mode == "fake":
        fake = FakeProvider()
        return Providers(llm=fake, stt=fake)
    key = settings.groq_api_key.get_secret_value() if settings.groq_api_key else ""
    if not key:
        raise LiveProvidersUnavailableError("AI_MODE=live needs GROQ_API_KEY")
    groq = GroqProvider(key, settings.ai_timeout_llm_seconds, settings.ai_timeout_stt_seconds)
    return Providers(llm=groq, stt=groq)
