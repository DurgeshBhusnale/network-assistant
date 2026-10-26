# Evals

Offline quality checks for prompts and models (method: `docs/05-AI-PROMPTS-AND-EVALS.md`). Never run in CI; they call live providers.

Arrives in Sprint 3:

- `data/drafts.jsonl` — draft golden set (format in doc 05; anonymised: real first names replaced).
- `data/extraction.jsonl` — capture extraction golden set.
- `run.py` — `uv run python evals/run.py --task draft --provider groq --model openai/gpt-oss-120b --set evals/data/drafts.jsonl --out evals/results/<date>-<model>.json`

`evals/results/` is git-ignored.
