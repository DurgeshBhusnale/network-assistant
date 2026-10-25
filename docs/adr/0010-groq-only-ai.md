# ADR-0010: Groq is the only AI provider in v1

- Status: Accepted (25 Oct 2026). Supersedes the provider routing in ADR-0003 (the single AI router, versioned prompts, timeouts, retries, JSON validation and cost logging still apply).

## Context
The founder wants one AI provider to keep accounts, keys, billing and data-processor notices simple. Report 4 priced a Groq-only stack at about ₹9 AI cost per Sprint user per month, the cheapest sensible option.

## Decision
- All AI tasks use Groq: `openai/gpt-oss-20b` for extraction, relevance, fact check and style (fallback `openai/gpt-oss-120b`); `openai/gpt-oss-120b` for every draft (fallback `openai/gpt-oss-20b`); `whisper-large-v3-turbo` for speech-to-text in every language (fallback `whisper-large-v3`).
- Free and paid users use the same models; plans differ in limits only. Rule 5 ("no frontier models for free") is met by construction.
- Anthropic, Sarvam and OpenAI stay on the approved list but are not integrated, configured or named as processors in v1.
- Model ids stay in env (`MODEL_SMALL`, `MODEL_FALLBACK_SMALL`, `MODEL_DRAFT`, `MODEL_FALLBACK_DRAFT`, `MODEL_STT`, `MODEL_STT_FALLBACK`).

## Consequences
- A full Groq outage takes AI features down (drafts show a retry message); there is no cross-provider fallback.
- Hinglish/Hindi/Marathi transcription quality depends on Whisper; the Sprint 5 test decides whether to propose Sarvam in a new ADR.
- No premium-model drafts for senior contacts; revisit with beta edit ratios. Adding a provider later is a provider class plus env config.
