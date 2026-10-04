# 2–3 minute interview demo

## Before the interview

```bash
docker compose up --build
```

Open `http://localhost:8000/docs`, expand `POST /replies/analyze`, and keep the n8n workflow JSON
open in another tab.

## Script

**0:00–0:30 — Frame the problem**

“My other projects cover research and outbound creation. ReplySense covers what happens after a
prospect responds: it turns unstructured email into a safe, structured next action for a CRM or
automation workflow. It supports an LLM, but the operational policy is deterministic.”

**0:30–1:05 — Positive signal with human approval**

Submit `examples/payloads/meeting-request.json`. Point out `MEETING_REQUEST`, the preserved `next
week` phrase, `SCHEDULE_FOLLOW_UP`, and `requires_human_review: true`.

“The system recommends the step, but it does not schedule or send anything. A person owns the
high-impact action.”

**1:05–1:40 — Safety override**

Submit `examples/payloads/unsubscribe.json`. Point out 0.99 confidence, `SUPPRESS_CONTACT`, and no
human review. Then call `POST /replies/{id}/suggest-response`; it returns HTTP 409.

“This path is outside the model. Even if an LLM saw mixed positive language, the deterministic
unsubscribe rule wins, and the drafting endpoint is closed.”

**1:40–2:10 — Automation contract**

Use `POST /webhooks/reply` with `examples/payloads/not-now.json`. Show the flat response and then the
n8n Switch branches in `examples/replysense-n8n-workflow.json`.

“The original date language is preserved instead of inventing a calendar date. n8n can create a
follow-up task or send ambiguous cases to review.”

**2:10–2:40 — Engineering evidence**

Show the test names and mention the quality gate: pytest, Ruff, strict mypy, and startup smoke test.
Close with the honest limitation: without an API key, the fallback is conservative and less nuanced;
its purpose is resilience and a runnable demo, not parity with the model.

