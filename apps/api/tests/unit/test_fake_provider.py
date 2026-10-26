import json
from pathlib import Path

import pytest

from app.ai.base import LLMRequest, TranscribeRequest
from app.ai.factory import LiveProvidersUnavailableError, build_providers
from app.ai.providers.fake import FakeProvider, FixtureNotFoundError
from app.core.config import Settings


def _request(task: str = "draft") -> LLMRequest:
    return LLMRequest(task=task, prompt_version="draft.v1", model="m", prompt="hello there")  # type: ignore[arg-type]


async def test_fake_provider_returns_fixture_deterministically() -> None:
    provider = FakeProvider()

    first = await provider.complete(_request())
    second = await provider.complete(_request())

    assert first == second
    assert first.provider == "fake"
    assert json.loads(first.text)["message"].startswith("Hey Ananya")


@pytest.mark.parametrize(
    "task", ["extract_people", "label_relevance", "draft", "factcheck", "summarise_style"]
)
async def test_fake_provider_has_a_fixture_per_task(task: str) -> None:
    result = await FakeProvider().complete(_request(task))
    assert result.text


async def test_fake_provider_style_summary_is_json() -> None:
    result = await FakeProvider().complete(_request("summarise_style"))
    assert json.loads(result.text)["summary"].startswith("Starts with")


async def test_fake_transcribe_uses_language_hint() -> None:
    request = TranscribeRequest(audio=b"\x00", mime="audio/webm", model="stt", language_hint="hi")
    transcript = await FakeProvider().transcribe(request)
    assert transcript.language == "hi"
    assert "Priya" in transcript.text


async def test_fake_provider_missing_fixture_raises(tmp_path: Path) -> None:
    with pytest.raises(FixtureNotFoundError):
        await FakeProvider(fixtures_dir=tmp_path).complete(_request())


def test_ai_mode_fake_builds_fake_providers() -> None:
    providers = build_providers(Settings(ai_mode="fake"))
    assert providers.llm.name == "fake"
    assert providers.stt.name == "fake"


def test_ai_mode_live_needs_a_groq_key() -> None:
    with pytest.raises(LiveProvidersUnavailableError):
        build_providers(Settings(ai_mode="live", groq_api_key=None))
