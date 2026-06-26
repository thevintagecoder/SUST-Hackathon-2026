from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.analyzer import investigate_ticket
from app.safety import sanitize_response
from app.schemas import TicketRequest, TicketResponse


app = FastAPI(
    title="QueueStorm Investigator",
    version="1.0.0",
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request,
    exception: RequestValidationError,
) -> JSONResponse:
    """
    Handle malformed JSON and request-schema violations safely.

    We intentionally do not return FastAPI's detailed validation
    information because it may repeat submitted customer data.
    """

    return JSONResponse(
        status_code=400,
        content={
            "detail": (
                "Invalid request body. Check the required fields, "
                "data types, and enum values."
            )
        },
    )


@app.exception_handler(Exception)
async def unexpected_exception_handler(
    request: Request,
    exception: Exception,
) -> JSONResponse:
    """
    Return a generic response for unexpected internal failures.

    Do not expose:
    - stack traces
    - exception details
    - local file paths
    - environment variables
    - API keys or other secrets
    """

    return JSONResponse(
        status_code=500,
        content={
            "detail": (
                "An internal error occurred while analyzing the ticket."
            )
        },
    )


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(
    "/analyze-ticket",
    response_model=TicketResponse,
)
def analyze_ticket(
    ticket: TicketRequest,
) -> TicketResponse:
    """
    Analyze a complaint together with its transaction evidence.
    """

    # The JSON structure is valid, but the complaint has no
    # meaningful content. This is a semantic 422 error.
    if not ticket.complaint.strip():
        raise HTTPException(
            status_code=422,
            detail="Complaint must not be empty.",
        )

    investigation_result = investigate_ticket(ticket)

    # Every successful result passes through the final safety guard.
    return sanitize_response(investigation_result)