"""Deterministic provider for AI_MODE=fake (tests, CI, local dev). Never touches the network."""

import json
from pathlib import Path

from app.ai.base import LLMRequest, LLMResult, TranscribeRequest, Transcript

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fake" / "fixtures"


class FixtureNotFoundError(LookupError):
    pass


class FakeProvider:
    name = "fake"

    def __init__(self, fixtures_dir: Path = FIXTURES_DIR) -> None:
        self._dir = fixtures_dir

    def _load(self, name: str) -> dict[str, object]:
        path = self._dir / f"{name}.json"
        if not path.is_file():
            raise FixtureNotFoundError(f"No fake AI fixture for {name!r}")
        data: dict[str, object] = json.loads(path.read_text(encoding="utf-8"))
        return data

    async def complete(self, request: LLMRequest) -> LLMResult:
        output = self._load(request.task)["output"]
        text = json.dumps(output, ensure_ascii=False) if request.json_output else str(output)
        return LLMResult(
            text=text,
            provider=self.name,
            model=request.model or "fake",
            tokens_in=len(request.prompt.split()),
            tokens_out=len(text.split()),
            latency_ms=0,
        )

    async def transcribe(self, request: TranscribeRequest) -> Transcript:
        fixture = self._load("transcribe")
        return Transcript(
            text=str(fixture["text"]),
            language=request.language_hint or str(fixture["language"]),
            audio_seconds=float(str(fixture["audio_seconds"])),
            provider=self.name,
            model=request.model or "fake",
            latency_ms=0,
        )
