from typing import Any

import httpx
import pytest

from app.schemas import ExtractedEntities, LLMAnalysis
from tests.conftest import AppFactory


async def analyze(
    client: httpx.AsyncClient, body: str, subject: str = "Re: hello"
) -> dict[str, Any]:
    response = await client.post(
        "/replies/analyze",
        json={"from_email": "prospect@example.com", "subject": subject, "body": body},
    )
    assert response.status_code == 201, response.text
    result: dict[str, Any] = response.json()
    return result


@pytest.mark.asyncio
async def test_health(client: httpx.AsyncClient) -> None:
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "replysense"}


@pytest.mark.asyncio
async def test_interested_classification(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Sounds useful. I'm interested in learning more.")
    assert data["analysis"]["classification"] == "INTERESTED"
    assert data["analysis"]["recommended_action"] == "HUMAN_REVIEW"
    assert data["analysis"]["requires_human_review"] is True


@pytest.mark.asyncio
async def test_meeting_request_and_relative_time(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Can you show me how this works sometime next week?")
    assert data["analysis"]["classification"] == "MEETING_REQUEST"
    assert "next week" in data["analysis"]["extracted_entities"]["relative_times"]
    assert data["analysis"]["requires_human_review"] is True


@pytest.mark.asyncio
async def test_not_now_preserves_ambiguous_date(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Not right now. Reach back out in January.")
    analysis = data["analysis"]
    assert analysis["classification"] == "NOT_NOW"
    assert analysis["recommended_action"] == "CREATE_FOLLOW_UP_TASK"
    assert analysis["extracted_entities"]["dates"] == ["January"]


@pytest.mark.asyncio
async def test_explicit_unsubscribe(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Please take me off your list.")
    analysis = data["analysis"]
    assert analysis["classification"] == "UNSUBSCRIBE"
    assert analysis["recommended_action"] == "SUPPRESS_CONTACT"
    assert analysis["requires_human_review"] is False


class ConflictingLLM:
    async def analyze(self, *, subject: str | None, body: str) -> LLMAnalysis | None:
        return LLMAnalysis(
            classification="INTERESTED",
            confidence=1,
            sentiment="positive",
            reasoning_summary="Claims interest.",
            entities=ExtractedEntities(),
        )


async def custom_client(app_factory: AppFactory, llm: Any) -> tuple[httpx.AsyncClient, Any]:
    app = app_factory(llm)
    context = app.router.lifespan_context(app)
    await context.__aenter__()
    client = httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test")
    return client, context


@pytest.mark.asyncio
async def test_unsubscribe_overrides_conflicting_llm(app_factory: AppFactory) -> None:
    test_client, context = await custom_client(app_factory, ConflictingLLM())
    try:
        data = await analyze(test_client, "I am interested, but unsubscribe and do not contact me.")
    finally:
        await test_client.aclose()
        await context.__aexit__(None, None, None)
    assert data["analysis"]["classification"] == "UNSUBSCRIBE"
    assert data["analysis"]["recommended_action"] == "SUPPRESS_CONTACT"


@pytest.mark.asyncio
async def test_bounce_detection(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Delivery failed: 550 5.1.1 user unknown")
    assert data["analysis"]["classification"] == "BOUNCE"
    assert data["analysis"]["recommended_action"] == "MARK_EMAIL_INVALID"


@pytest.mark.asyncio
async def test_out_of_office_not_interest(client: httpx.AsyncClient) -> None:
    data = await analyze(
        client,
        "Automatic reply: I am out of the office. This sounds interesting; I return Monday.",
    )
    assert data["analysis"]["classification"] == "OUT_OF_OFFICE"


@pytest.mark.asyncio
async def test_wrong_person_and_referral(client: httpx.AsyncClient) -> None:
    wrong = await analyze(client, "I am not the right person for this.")
    assert wrong["analysis"]["classification"] == "WRONG_PERSON"
    referral = await analyze(
        client, "I'm not the right person. Contact Jane Doe at jane@example.com."
    )
    assert referral["analysis"]["classification"] == "REFERRAL"
    assert referral["analysis"]["extracted_entities"]["referred_email"] == "jane@example.com"
    assert referral["analysis"]["extracted_entities"]["referred_contact"] == "Jane Doe"


class MalformedLLM:
    async def analyze(self, *, subject: str | None, body: str) -> Any:
        return {"classification": "MADE_UP", "confidence": "certain"}


@pytest.mark.asyncio
async def test_malformed_llm_result_cannot_crash_api(app_factory: AppFactory) -> None:
    test_client, context = await custom_client(app_factory, MalformedLLM())
    try:
        data = await analyze(test_client, "Sounds useful, tell me more.")
    finally:
        await test_client.aclose()
        await context.__aexit__(None, None, None)
    assert data["analysis"]["classification"] == "INTERESTED"


@pytest.mark.asyncio
async def test_missing_information_is_not_fabricated(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Thanks for the note.")
    entities = data["analysis"]["extracted_entities"]
    assert entities["dates"] == []
    assert entities["relative_times"] == []
    assert "referred_contact" not in entities
    assert "company_name" not in entities


@pytest.mark.asyncio
async def test_unsubscribe_and_bounce_never_generate_suggested_reply(
    client: httpx.AsyncClient,
) -> None:
    unsubscribe = await analyze(client, "Unsubscribe me.")
    unsub_id = unsubscribe["reply"]["id"]
    assert (await client.post(f"/replies/{unsub_id}/suggest-response")).status_code == 409
    bounce = await analyze(client, "Mailbox unavailable: user unknown")
    bounce_id = bounce["reply"]["id"]
    assert (await client.post(f"/replies/{bounce_id}/suggest-response")).status_code == 409


@pytest.mark.asyncio
async def test_supported_suggested_reply_is_saved(client: httpx.AsyncClient) -> None:
    data = await analyze(client, "Sounds useful. I'm interested.", subject="Product")
    response = await client.post(f"/replies/{data['reply']['id']}/suggest-response")
    assert response.status_code == 201
    assert response.json()["subject"] == "Re: Product"


@pytest.mark.asyncio
async def test_webhook_returns_flat_workflow_json(client: httpx.AsyncClient) -> None:
    response = await client.post(
        "/webhooks/reply",
        json={"from_email": "alex@example.com", "body": "Check back next month."},
    )
    assert response.status_code == 201
    assert response.json()["classification"] == "NOT_NOW"
    assert response.json()["recommended_action"] == "CREATE_FOLLOW_UP_TASK"


@pytest.mark.asyncio
async def test_webhook_payload_validation(client: httpx.AsyncClient) -> None:
    missing = await client.post("/webhooks/reply", json={"from_email": "alex@example.com"})
    assert missing.status_code == 422
    invalid_email = await client.post(
        "/webhooks/reply", json={"from_email": "not-an-email", "body": "Hello"}
    )
    assert invalid_email.status_code == 422
