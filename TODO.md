# ReplySense implementation plan

- [x] Define project configuration, dependencies, linting, typing, and Docker setup.
- [x] Implement SQLAlchemy persistence and Pydantic API/domain schemas.
- [x] Implement deterministic safety rules, fallback classification, entity extraction, action mapping, and response drafting.
- [x] Add an OpenAI-compatible LLM client with strict structured-output validation and safe failure handling.
- [x] Build the FastAPI routes for health, reply analysis/history, suggested responses, and automation webhooks.
- [x] Add meaningful API and service tests for classification, safety overrides, malformed LLM output, and validation.
- [x] Create portfolio documentation, example payloads, and an importable n8n workflow.
- [x] Run pytest, Ruff checks/format verification, strict mypy, and an application startup smoke test; fix all failures.
