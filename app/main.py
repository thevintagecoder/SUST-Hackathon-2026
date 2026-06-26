from fastapi import FastAPI, HTTPException

from app.schemas import (
    CaseType,
    Department,
    EvidenceVerdict,
    Severity,
    TicketRequest,
    TicketResponse,
)


app = FastAPI(
    title="QueueStorm Investigator",
    version="1.0.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze-ticket", response_model=TicketResponse)
def analyze_ticket(ticket: TicketRequest) -> TicketResponse:
    """
    Temporary placeholder endpoint.

    This currently returns a safe generic response so we can verify
    that the request and response schemas work correctly.
    """

    if not ticket.complaint.strip():
        raise HTTPException(
            status_code=422,
            detail="Complaint must not be empty.",
        )

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        relevant_transaction_id=None,
        evidence_verdict=EvidenceVerdict.INSUFFICIENT_DATA,
        case_type=CaseType.OTHER,
        severity=Severity.LOW,
        department=Department.CUSTOMER_SUPPORT,
        agent_summary=(
            "The complaint was received, but automated investigation "
            "logic has not yet been applied."
        ),
        recommended_next_action=(
            "Review the complaint and transaction history to identify "
            "the relevant transaction and issue."
        ),
        customer_reply=(
            "Thank you for reaching out. We have received your concern "
            "and will review the available details. Please do not share "
            "your PIN, OTP, or password with anyone."
        ),
        human_review_required=False,
        confidence=0.30,
        reason_codes=["placeholder_analysis"],
    )