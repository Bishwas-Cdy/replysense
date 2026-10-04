# n8n integration

The included workflow is a provider-neutral example. It receives a webhook, sends the normalized
payload to ReplySense, and branches on the returned `classification`.

```text
Email / Webhook Trigger
        ↓
ReplySense POST /webhooks/reply
        ↓
Switch on classification
        ├── INTERESTED / MEETING_REQUEST / QUESTION → human review
        ├── NOT_NOW → create follow-up task
        ├── WRONG_PERSON / REFERRAL → enrichment or routing workflow
        ├── UNSUBSCRIBE → suppression list
        ├── BOUNCE → mark email invalid
        └── other → manual triage
```

## Import and run

1. Start ReplySense with `docker compose up --build`.
2. In n8n, choose **Import from File** and select
   `examples/replysense-n8n-workflow.json`.
3. If n8n runs on the host, keep `http://localhost:8000`. If it runs in Docker, change the HTTP
   Request URL to `http://host.docker.internal:8000/webhooks/reply` (or the ReplySense service name
   when both containers share a network).
4. Activate the workflow or use **Listen for test event**.
5. POST one of the example payloads to the n8n webhook URL.

The example ends each branch in a named no-op node. Replace those nodes with the relevant CRM,
task, suppression, Slack, or enrichment integration. No real credentials are included.

## Input contract

```json
{
  "from_email": "alex@example.com",
  "subject": "Re: AI research",
  "body": "Not right now, check back in January.",
  "received_at": "2026-10-04T12:00:00Z"
}
```

Only `body` is required. `received_at` must be ISO 8601 when supplied.

## Output fields for branching

- `reply_id` and `analysis_id`: persistence references
- `classification`: stable Switch value
- `confidence`: model/fallback confidence, not permission to automate
- `entities`: verbatim extracted facts
- `recommended_action`: deterministic policy output
- `requires_human_review`: approval gate
- `reasoning_summary`: concise audit context

For a production integration, add webhook authentication, idempotency, retry/dead-letter handling,
and monitoring before connecting action nodes.

