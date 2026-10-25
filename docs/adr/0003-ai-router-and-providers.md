# ADR-0003: One AI router; Groq for volume, Claude for high-stakes drafts

- Status: Accepted (25 Oct 2026)

## Context
Report 4 priced the same workload across providers. AI cost per Career Sprint user per month: Groq-only ≈ ₹9, DeepSeek ≈ ₹14, Sarvam ≈ ₹22, Groq + Claude polish ≈ ₹22, Claude Haiku + Sonnet ≈ ₹23, Gemini ≈ ₹27, OpenAI ≈ ₹43, xAI Grok 4.3 ≈ ₹97. Among sensible options, margin differs by ~4 points; draft quality and data location matter more than price.

## Decision
- All AI calls go through `app/ai/router.py` with per-task routing, timeouts, retries, fallback, JSON validation and cost logging (`ai_calls`).
- Groq `openai/gpt-oss-20b` for extraction, relevance, fact check, style summary; `openai/gpt-oss-120b` for default drafts; Groq `whisper-large-v3-turbo` for English STT.
- Claude Sonnet 5.5 for paid ask-stage drafts to senior contacts and repeated "Another version"; Claude Haiku 5.5 as fallback for small tasks.
- Sarvam STT for Hindi/Marathi/Hinglish voice notes (final routing after the Sprint 5 test).
- Approved providers only: Groq, Anthropic, Sarvam, OpenAI (STT fallback). No DeepSeek first-party API (data transfer risk). OpenRouter allowed only for prototyping.
- Model IDs from env; prompts versioned; changes require an eval run.

## Consequences
- Provider swaps are config changes. Blind test Groq vs Claude drafts before Sprint 3 ends and revisit routing.
