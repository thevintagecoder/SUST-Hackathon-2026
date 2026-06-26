import json

from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


client = TestClient(app)

# This client allows us to examine the API's controlled 500 response
# instead of causing pytest to re-raise the original exception.
error_client = TestClient(
    app,
    raise_server_exceptions=False,
)


def test_valid_minimal_request_returns_200() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "VALID-001",
            "complaint": "Something is wrong with my money.",
        },
    )

    assert response.status_code == 200
    assert response.json()["ticket_id"] == "VALID-001"


def test_invalid_json_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        content='{"ticket_id": "BAD-JSON", "complaint": ',
        headers={
            "Content-Type": "application/json",
        },
    )

    assert response.status_code == 400

    assert response.json() == {
        "detail": (
            "Invalid request body. Check the required fields, "
            "data types, and enum values."
        )
    }


def test_missing_ticket_id_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "complaint": "My payment failed.",
        },
    )

    assert response.status_code == 400


def test_missing_complaint_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "MISSING-COMPLAINT",
        },
    )

    assert response.status_code == 400


def test_blank_complaint_returns_422() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "BLANK-COMPLAINT",
            "complaint": "     ",
        },
    )

    assert response.status_code == 422

    assert response.json() == {
        "detail": "Complaint must not be empty."
    }


def test_empty_ticket_id_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "",
            "complaint": "My payment failed.",
        },
    )

    assert response.status_code == 400


def test_invalid_language_enum_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "INVALID-LANGUAGE",
            "complaint": "My payment failed.",
            "language": "english",
        },
    )

    assert response.status_code == 400


def test_invalid_channel_enum_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "INVALID-CHANNEL",
            "complaint": "My payment failed.",
            "channel": "chat",
        },
    )

    assert response.status_code == 400


def test_invalid_transaction_type_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "INVALID-TYPE",
            "complaint": "Please check this transaction.",
            "transaction_history": [
                {
                    "transaction_id": "TXN-001",
                    "timestamp": "2026-04-14T10:00:00Z",
                    "type": "send_money",
                    "amount": 500,
                    "counterparty": "+8801700000000",
                    "status": "completed",
                }
            ],
        },
    )

    assert response.status_code == 400


def test_invalid_transaction_status_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "INVALID-STATUS",
            "complaint": "Please check this transaction.",
            "transaction_history": [
                {
                    "transaction_id": "TXN-002",
                    "timestamp": "2026-04-14T10:00:00Z",
                    "type": "transfer",
                    "amount": 500,
                    "counterparty": "+8801700000000",
                    "status": "successful",
                }
            ],
        },
    )

    assert response.status_code == 400


def test_negative_transaction_amount_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "NEGATIVE-AMOUNT",
            "complaint": "Please check this transaction.",
            "transaction_history": [
                {
                    "transaction_id": "TXN-003",
                    "timestamp": "2026-04-14T10:00:00Z",
                    "type": "transfer",
                    "amount": -500,
                    "counterparty": "+8801700000000",
                    "status": "completed",
                }
            ],
        },
    )

    assert response.status_code == 400


def test_missing_transaction_field_returns_400() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "INCOMPLETE-TRANSACTION",
            "complaint": "Please check this transaction.",
            "transaction_history": [
                {
                    "transaction_id": "TXN-004",
                    "type": "transfer",
                    "amount": 500,
                    "counterparty": "+8801700000000"
                }
            ],
        },
    )

    assert response.status_code == 400


def test_omitted_transaction_history_is_accepted() -> None:
    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "NO-HISTORY",
            "complaint": "Something is wrong with my money.",
        },
    )

    assert response.status_code == 200

    body = response.json()

    assert body["relevant_transaction_id"] is None
    assert body["evidence_verdict"] == "insufficient_data"


def test_error_response_does_not_echo_sensitive_input() -> None:
    secret_value = "SECRET-SHOULD-NOT-BE-ECHOED"

    response = client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "SENSITIVE-ERROR",
            "complaint": secret_value,
            "language": "not-a-valid-language",
        },
    )

    assert response.status_code == 400
    assert secret_value not in response.text


def test_unexpected_exception_returns_safe_500(
    monkeypatch,
) -> None:
    def raise_unexpected_error(ticket):
        raise RuntimeError(
            "Database password=super-secret-value "
            "at /Users/example/private/project.py"
        )

    monkeypatch.setattr(
        main_module,
        "investigate_ticket",
        raise_unexpected_error,
    )

    response = error_client.post(
        "/analyze-ticket",
        json={
            "ticket_id": "INTERNAL-ERROR",
            "complaint": "Please check my transaction.",
        },
    )

    assert response.status_code == 500

    assert response.json() == {
        "detail": (
            "An internal error occurred while analyzing the ticket."
        )
    }

    response_text = response.text.lower()

    assert "super-secret-value" not in response_text
    assert "runtimeerror" not in response_text
    assert "/users/example" not in response_text
    assert "traceback" not in response_text