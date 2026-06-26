import json
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)

SAMPLE_FILE = (
    Path(__file__).parent
    / "fixtures"
    / "SUST_Preli_Sample_Cases.json"
)

# These are the fields that represent the main investigation decision.
DECISION_FIELDS = [
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "human_review_required",
]

# These fields are required by the API contract.
REQUIRED_RESPONSE_FIELDS = [
    "ticket_id",
    "relevant_transaction_id",
    "evidence_verdict",
    "case_type",
    "severity",
    "department",
    "agent_summary",
    "recommended_next_action",
    "customer_reply",
    "human_review_required",
]

VALID_EVIDENCE_VERDICTS = {
    "consistent",
    "inconsistent",
    "insufficient_data",
}

VALID_CASE_TYPES = {
    "wrong_transfer",
    "payment_failed",
    "refund_request",
    "duplicate_payment",
    "merchant_settlement_delay",
    "agent_cash_in_issue",
    "phishing_or_social_engineering",
    "other",
}

VALID_SEVERITIES = {
    "low",
    "medium",
    "high",
    "critical",
}

VALID_DEPARTMENTS = {
    "customer_support",
    "dispute_resolution",
    "payments_ops",
    "merchant_operations",
    "agent_operations",
    "fraud_risk",
}


def load_sample_cases() -> list[dict[str, Any]]:
    """
    Load the ten official public sample cases.
    """

    if not SAMPLE_FILE.exists():
        raise FileNotFoundError(
            f"Sample file was not found at: {SAMPLE_FILE}"
        )

    with SAMPLE_FILE.open(
        mode="r",
        encoding="utf-8",
    ) as file:
        data = json.load(file)

    return data["cases"]


SAMPLE_CASES = load_sample_cases()


def case_id(case: dict[str, Any]) -> str:
    """
    Give every parametrized test a readable name.
    """

    return f'{case["id"]} - {case["label"]}'


def find_decision_mismatches(
    actual: dict[str, Any],
    expected: dict[str, Any],
) -> list[str]:
    """
    Compare the main decision fields and return readable differences.
    """

    mismatches: list[str] = []

    for field in DECISION_FIELDS:
        actual_value = actual.get(field)
        expected_value = expected.get(field)

        if actual_value != expected_value:
            mismatches.append(
                f"{field}: expected {expected_value!r}, "
                f"received {actual_value!r}"
            )

    return mismatches


@pytest.mark.parametrize(
    "case",
    SAMPLE_CASES,
    ids=case_id,
)
def test_public_sample_decisions(
    case: dict[str, Any],
) -> None:
    """
    Send each official input to the API and compare the main
    investigation decisions with the official expected output.
    """

    response = client.post(
        "/analyze-ticket",
        json=case["input"],
    )

    assert response.status_code == 200, (
        f'{case["id"]} returned HTTP {response.status_code}.\n'
        f"Response: {response.text}"
    )

    actual = response.json()
    expected = case["expected_output"]

    mismatches = find_decision_mismatches(
        actual=actual,
        expected=expected,
    )

    assert not mismatches, (
        f'{case["id"]} — {case["label"]} failed:\n'
        + "\n".join(f"  - {item}" for item in mismatches)
    )


@pytest.mark.parametrize(
    "case",
    SAMPLE_CASES,
    ids=case_id,
)
def test_public_sample_response_schema(
    case: dict[str, Any],
) -> None:
    """
    Confirm every public sample response contains the required
    fields and valid enum values.
    """

    response = client.post(
        "/analyze-ticket",
        json=case["input"],
    )

    assert response.status_code == 200

    body = response.json()

    missing_fields = [
        field
        for field in REQUIRED_RESPONSE_FIELDS
        if field not in body
    ]

    assert not missing_fields, (
        f'{case["id"]} is missing required response fields: '
        f"{missing_fields}"
    )

    assert body["ticket_id"] == case["input"]["ticket_id"]

    assert (
        body["evidence_verdict"]
        in VALID_EVIDENCE_VERDICTS
    )

    assert body["case_type"] in VALID_CASE_TYPES
    assert body["severity"] in VALID_SEVERITIES
    assert body["department"] in VALID_DEPARTMENTS

    assert isinstance(
        body["human_review_required"],
        bool,
    )

    assert isinstance(body["agent_summary"], str)
    assert body["agent_summary"].strip()

    assert isinstance(
        body["recommended_next_action"],
        str,
    )
    assert body["recommended_next_action"].strip()

    assert isinstance(body["customer_reply"], str)
    assert body["customer_reply"].strip()

    if body.get("confidence") is not None:
        assert isinstance(
            body["confidence"],
            (int, float),
        )
        assert 0 <= body["confidence"] <= 1

    if body.get("reason_codes") is not None:
        assert isinstance(body["reason_codes"], list)
        assert all(
            isinstance(reason, str)
            for reason in body["reason_codes"]
        )


@pytest.mark.parametrize(
    "case",
    SAMPLE_CASES,
    ids=case_id,
)
def test_public_sample_customer_reply_safety(
    case: dict[str, Any],
) -> None:
    """
    Detect common unsafe customer-reply phrases.

    Safe warnings such as 'do not share your OTP' are allowed.
    """

    response = client.post(
        "/analyze-ticket",
        json=case["input"],
    )

    assert response.status_code == 200

    body = response.json()
    reply = body["customer_reply"].lower()

    unsafe_credential_requests = [
        "send us your otp",
        "send your otp",
        "provide your otp",
        "tell us your otp",
        "share your otp with us",
        "send us your pin",
        "provide your pin",
        "tell us your pin",
        "share your pin with us",
        "send us your password",
        "provide your password",
        "tell us your password",
        "share your password with us",
        "provide your full card number",
        "send your full card number",
    ]

    unsafe_financial_promises = [
        "we will refund you",
        "we will refund your money",
        "we guarantee a refund",
        "your money will definitely be returned",
        "we will reverse the transaction",
        "we guarantee recovery",
        "your account will be unblocked",
    ]

    found_unsafe_phrases = [
        phrase
        for phrase in (
            unsafe_credential_requests
            + unsafe_financial_promises
        )
        if phrase in reply
    ]

    assert not found_unsafe_phrases, (
        f'{case["id"]} contains unsafe customer-reply language: '
        f"{found_unsafe_phrases}\n"
        f"Reply: {body['customer_reply']}"
    )


def test_health_endpoint() -> None:
    """
    The judge checks this endpoint before sending tickets.
    """

    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_empty_complaint_is_rejected() -> None:
    """
    A structurally valid but empty complaint should fail safely.
    """

    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TEST-EMPTY",
            "complaint": "   ",
        },
    )

    assert response.status_code == 422


def test_missing_ticket_id_is_rejected() -> None:
    """
    ticket_id is a required request field.
    """

    response = client.post(
        "/analyze-ticket",
        json={
            "complaint": "My payment failed.",
        },
    )

    assert response.status_code in {400, 422}


def test_invalid_enum_is_rejected() -> None:
    """
    Invalid enum spellings must not be silently accepted.
    """

    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "TEST-ENUM",
            "complaint": "My payment failed.",
            "language": "english",
            "channel": "chat",
        },
    )

    assert response.status_code in {400, 422}