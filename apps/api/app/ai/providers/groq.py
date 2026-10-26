"""Groq (OpenAI-compatible) chat and speech-to-text. The only live provider in v1 (ADR-0010)."""

import time

import httpx

from app.ai.base import LLMRequest, LLMResult, ProviderError, TranscribeRequest, Transcript

BASE_URL = "https://api.groq.com/openai/v1"


def _raise_for(response: httpx.Response) -> None:
    if response.status_code == 429 or response.status_code >= 500:
        raise ProviderError(f"groq {response.status_code}", retryable=True)
    if response.status_code >= 400:
        raise ProviderError(f"groq {response.status_code}", retryable=False)


class GroqProvider:
    name = "groq"

    def __init__(self, api_key: str, llm_timeout: float, stt_timeout: float) -> None:
        self._client = httpx.AsyncClient(
            base_url=BASE_URL, headers={"Authorization": f"Bearer {api_key}"}
        )
        self._llm_timeout = llm_timeout
        self._stt_timeout = stt_timeout

    async def complete(self, request: LLMRequest) -> LLMResult:
        body: dict[str, object] = {
            "model": request.model,
            "messages": [{"role": "user", "content": request.prompt}],
            "temperature": request.temperature,
            "max_completion_tokens": request.max_tokens,
        }
        if request.model.startswith("openai/gpt-oss"):
            body["reasoning_effort"] = "low"
        if request.json_output:
            body["response_format"] = {"type": "json_object"}
        started = time.perf_counter()
        try:
            response = await self._client.post(
                "/chat/completions", json=body, timeout=self._llm_timeout
            )
        except httpx.TimeoutException as exc:
            raise ProviderError("groq timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("groq network error", retryable=True) from exc
        _raise_for(response)
        data = response.json()
        usage = data.get("usage") or {}
        return LLMResult(
            text=data["choices"][0]["message"].get("content") or "",
            provider=self.name,
            model=request.model,
            tokens_in=int(usage.get("prompt_tokens", 0)),
            tokens_out=int(usage.get("completion_tokens", 0)),
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def transcribe(self, request: TranscribeRequest) -> Transcript:
        extension = request.mime.split("/")[-1].split(";")[0] or "webm"
        data: dict[str, str] = {"model": request.model, "response_format": "verbose_json"}
        if request.language_hint in ("en", "hi", "mr"):
            data["language"] = request.language_hint
        started = time.perf_counter()
        try:
            response = await self._client.post(
                "/audio/transcriptions",
                data=data,
                files={"file": (f"audio.{extension}", request.audio, request.mime)},
                timeout=self._stt_timeout,
            )
        except httpx.TimeoutException as exc:
            raise ProviderError("groq stt timeout", retryable=True) from exc
        except httpx.HTTPError as exc:
            raise ProviderError("groq stt network error", retryable=True) from exc
        _raise_for(response)
        body = response.json()
        return Transcript(
            text=body.get("text", ""),
            language=body.get("language"),
            audio_seconds=float(body.get("duration") or 0.0),
            provider=self.name,
            model=request.model,
            latency_ms=int((time.perf_counter() - started) * 1000),
        )

    async def aclose(self) -> None:
        await self._client.aclose()
