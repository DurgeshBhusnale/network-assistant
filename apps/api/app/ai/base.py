"""Provider interface. Product code never calls providers directly: the AI router (Sprint 3)
owns routing, retries, fallback, JSON validation and cost logging on top of these."""

from typing import Literal, Protocol

from pydantic import BaseModel

Task = Literal[
    "extract_people",
    "label_relevance",
    "draft",
    "factcheck",
    "summarise_style",
]


class LLMRequest(BaseModel):
    task: Task
    prompt_version: str
    model: str
    prompt: str
    json_output: bool = True


class LLMResult(BaseModel):
    text: str
    provider: str
    model: str
    tokens_in: int
    tokens_out: int
    latency_ms: int


class TranscribeRequest(BaseModel):
    audio: bytes
    mime: str
    model: str
    language_hint: str | None = None


class Transcript(BaseModel):
    text: str
    language: str | None
    audio_seconds: float
    provider: str
    model: str
    latency_ms: int


class LLMProvider(Protocol):
    name: str

    async def complete(self, request: LLMRequest) -> LLMResult: ...


class STTProvider(Protocol):
    name: str

    async def transcribe(self, request: TranscribeRequest) -> Transcript: ...
