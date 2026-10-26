# AI Prompts (v1) and Evaluation

Prompts live as versioned files in `apps/api/app/ai/prompts/<name>.v<N>.md` with `{{placeholders}}`. Copy the v1 texts below in Sprint 3. **Any change to a prompt = new version file + eval run before switching.** The `prompt_version` is stored on every output.

General rules for all prompts:
- Instructions first, then data inside clearly delimited tags (`<contact>…</contact>`). Treat everything inside data tags as data, never as instructions (user notes may contain text like "ignore previous instructions").
- Never include phone numbers or email addresses in prompts. Every input (including memory text and transcripts) passes through the PII scrubber first.
- Structured tasks return JSON only, validated by Pydantic; on invalid JSON, one repair retry ("Return only valid JSON matching the schema").

---

## 1. `extract_people.v1` (capture pipeline)

**Model:** Groq gpt-oss-20B (fallback gpt-oss-120B). **Output:** JSON.

```
You turn a short note about meeting people into structured records.

The note was written or spoken by the user on {{capture_datetime_local}} ({{timezone}}).
It may be in English, Hindi, Marathi or Hinglish, and may be messy or partial.

Rules:
- Extract every person the user met or mentioned as someone to follow up with.
- Only use information present in the note. Never invent names, companies, titles or dates.
- If a surname is missing, leave last_name null. If a company or title is unclear, use null.
- Facts are short third-person statements about the person ("wants help with AI agents").
- Commitments are things the user promised ("send him the deck").
- follow_up_date: resolve relative dates ("Monday", "next week", "in 3 days") against the capture date; return ISO YYYY-MM-DD or null. "Next week" with no day = the Monday of next week.
- where_met: event or place if stated.
- Put facts that belong to no specific person in unassigned_facts.

Return only JSON:
{
  "people": [
    {"first_name": str, "last_name": str|null, "company": str|null, "title": str|null,
     "where_met": str|null, "facts": [str], "commitments": [str], "follow_up_date": str|null}
  ],
  "unassigned_facts": [str]
}

<note>
{{transcript_or_text}}
</note>
```

## 2. `career_sprint.relevance.v1` (relevance labelling, batched ≤ 50)

**Model:** Groq gpt-oss-20B. **Output:** JSON.

```
The user is looking for a new job:
<goal>
Role: {{role}}
Target companies: {{companies}}
Locations: {{locations}}
</goal>

For each contact below, choose ONE label for how useful they are for this goal:
- "same_field": works in a similar role/field and could refer the user at their own company or knows openings.
- "can_introduce": likely knows people at target companies or in the field (e.g., recruiter, senior person, well-connected batchmate) based on the details given.
- "not_relevant": no evidence they can help with this goal.
Only use the details given. Do not guess based on names. Contacts at a target company were already labelled and are not included.

Return only JSON: {"labels": [{"id": str, "label": "same_field"|"can_introduce"|"not_relevant", "reason": str (max 12 words)}]}

<contacts>
{{#each contacts}}
{"id": "{{id}}", "title": "{{title}}", "company": "{{company}}", "how_known": "{{how_known}}", "notes": {{latest_3_memories_json}}}
{{/each}}
</contacts>
```

## 3. `style_summary.v1`

**Model:** Groq gpt-oss-20B. **Output:** text (≤ 80 words).

```
Describe how this person writes short messages to people they know, so someone else can imitate them.
Cover: greeting style, length, formality, use of Hinglish or Hindi words, emoji use, punctuation habits, sign-off.
Write ≤ 80 words as instructions ("Starts with 'Hey <name>!'. Short sentences. …"). Do not quote personal details from the samples.

<samples>
{{samples_joined_with_---}}
</samples>
```

## 4. `career_sprint.draft.v1`

**Model:** routed (tech spec §8.2). **Output:** JSON.

```
You write a short message that {{user_first_name}} will send personally, from their own WhatsApp or LinkedIn, to someone they know. It must sound exactly like them and be easy to send without edits.

Goal: {{user_first_name}} wants a {{role}} role{{#if companies}} at companies like {{companies}}{{/if}}.
Stage: {{stage}}
- warm_up: reconnect warmly. NO request of any kind. If <memories> or <history> give something specific, mention one of those details. If they are empty, keep it simple: a genuine hello that may mention their role or company from <contact>. Never invent a shared moment. End with a light, open question about them (how things are going, what they're enjoying lately), never about a specific project, launch or event you don't know about.
- ask: ask for a referral (or advice if they're not at a target company) in a specific, easy way: name the role{{#if job_link}} and include this link: {{job_link}}{{/if}}, offer to send a resume and a 2-line summary. Acknowledge their time.
- follow_up: one gentle, short nudge on the earlier message. No guilt.
- thank: thank them sincerely and specifically for what they did; share what happens next; no new ask.

Language: {{language}} ({{#if hinglish}}Hinglish = Hindi words in Latin script mixed naturally with English{{/if}}{{#if devanagari}}write in Devanagari{{/if}}).
Tone adjustment: {{tone or "none"}} (shorter = ≤ 40 words; warmer = more personal; more formal = respectful, no slang).
Writing style of {{user_first_name}}: {{style_summary or "friendly, concise, natural Indian English"}}
Examples of how they write:
<style_samples>{{up_to_3_samples}}</style_samples>

Hard rules:
- 2–4 short lines, maximum 90 words.
- Use ONLY facts from <contact>, <memories> and <history>. If you're unsure of a fact, leave it out.
- Never say you saw, read or heard something about them (a post, news, a launch, a move, a promotion, a trip, an event) unless it is in <memories> or <history>. Don't ask about events you only assume happened.
- Address them as {{contact_first_name}}. No sign-off with the sender's name. At most one emoji, only if the style uses emoji.
- No greeting-card language ("hope this message finds you well"), no "let's catch up sometime".

<contact>name: {{contact_name}}; title: {{title}}; company: {{company}}; how they know each other: {{how_known}}</contact>
<memories>{{memories_newest_first_max_20}}</memories>
<history>{{last_3_interactions}}</history>

Return only JSON: {"message": str, "facts_used": [str]}
```

## 5. `factcheck.v1`

**Model:** Groq gpt-oss-20B. **Output:** JSON.

```
Check a draft message against the known facts. List every factual claim in the draft about the recipient, the sender, or their shared history that is NOT supported by the facts. Greetings, wishes and opinions are not claims. Saying the sender saw, read, heard or noticed something about the recipient (a post, news, a launch, a move, a promotion, an event) IS a claim, and so is a question that assumes a specific event happened ("how's the new city?").

<facts>{{contact_fields_and_memories_and_goal}}</facts>
<draft>{{message}}</draft>

Return only JSON: {"unsupported": [str]}  (empty list if all claims are supported)
```

## 6. Ask detection (warm-up guard)

Rule first (case-insensitive regex list: `refer`, `referral`, `opening`, `resume`, `CV`, `job`, `could you help me`, `can you help me get`, `introduce me`, Hinglish variants `refer kar`, `job ke liye`), then if the rule fires on a warm-up, regenerate once with "This is a warm-up: remove any request." If it still fires, return with a warning.

---

## Evaluation

### Golden sets (`evals/data/`)

`drafts.jsonl` (start with 30 cases from concierge users, anonymised: real first names replaced, companies kept):

```json
{"id": "d001", "stage": "warm_up", "language": "en", "tone": null,
 "user": {"first_name": "Rohan", "style_summary": "…", "samples": ["…"]},
 "goal": {"role": "Backend Engineer", "companies": ["Razorpay", "Postman"]},
 "contact": {"name": "Ananya Kulkarni", "title": "SDE 2", "company": "Razorpay", "how_known": "ex-colleague at Infosys"},
 "memories": ["Offered to help if a role opens", "Moved to Bengaluru in March"],
 "history": ["sent: check-in 19 Oct", "replied 20 Oct"],
 "expect": {"no_ask": true, "must_mention_one_of": ["Bengaluru", "help"], "max_words": 90}}
```

`extraction.jsonl`: note text (+ optional audio file path) with expected people fields and follow-up date relative to a fixed capture datetime.

### Metrics

| Metric | How | Target (v1) |
|---|---|---|
| Rule compliance | Word count, ask rule, no phone/email/URL invented (code) | 100% |
| Factuality | `factcheck` judge with Groq gpt-oss-120B as judge (offline only) | ≥ 95% drafts with zero unsupported claims |
| Personal detail | Mentions ≥ 1 memory fact (warm_up/thank) | ≥ 90% |
| Would send | Blind human review (founder + 5 users), 1–5 scale | ≥ 70% score 4–5 |
| Extraction | Person-level F1 on name/company/title; exact follow-up date | F1 ≥ 0.9; date ≥ 95% |
| Latency / cost | From `ai_calls` | p95 < 6 s; cost per draft logged |

### Runner

`uv run python evals/run.py --task draft --provider groq --model openai/gpt-oss-120b --set evals/data/drafts.jsonl --out evals/results/<date>-<model>.json`

Produces a summary table and a CSV for blind review (model names hidden). Run before: changing a prompt version, changing a model, or changing routing. Record decisions in an ADR.
