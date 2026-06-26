from fastapi import FastAPI, HTTPException

from app.analyzer import investigate_ticket
from app.schemas import TicketRequest, TicketResponse


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
    Analyze a customer complaint together with recent transaction
    evidence.
    """

    if not ticket.complaint.strip():
        raise HTTPException(
            status_code=422,
            detail="Complaint must not be empty.",
        )

    return investigate_ticket(ticket)