import re

from app.schemas import TicketResponse


SAFE_CUSTOMER_REPLY = (
    "We have received your concern and will review it through the "
    "appropriate official support process. Please do not share your "
    "PIN, OTP, password, or full card information with anyone."
)

SAFE_NEXT_ACTION = (
    "Review the case through the approved internal workflow. "
    "Do not request sensitive credentials or confirm any refund, "
    "reversal, recovery, or account action before official verification."
)


# These patterns represent direct requests for sensitive credentials.
# Safe warnings such as "do not share your OTP" do not match them.
UNSAFE_CREDENTIAL_PATTERNS = [
    r"\bsend\s+(us\s+)?your\s+(pin|otp|password)\b",
    r"\bshare\s+your\s+(pin|otp|password)\s+with\s+(us|me)\b",
    r"\bprovide\s+(us\s+)?your\s+(pin|otp|password)\b",
    r"\btell\s+(us|me)\s+your\s+(pin|otp|password)\b",
    r"\bgive\s+(us|me)\s+your\s+(pin|otp|password)\b",
    r"\benter\s+your\s+(pin|otp|password)\b",
    r"\bsubmit\s+your\s+(pin|otp|password)\b",
    r"\bsend\s+(us\s+)?your\s+full\s+card\s+number\b",
    r"\bprovide\s+(us\s+)?your\s+full\s+card\s+number\b",
    r"\bshare\s+your\s+full\s+card\s+number\b",
]


# These phrases make unauthorized financial promises.
UNSAFE_FINANCIAL_PROMISE_PATTERNS = [
    r"\bwe\s+will\s+refund\b",
    r"\bwe'll\s+refund\b",
    r"\bwe\s+will\s+reverse\b",
    r"\bwe'll\s+reverse\b",
    r"\bwe\s+guarantee\s+(a\s+)?refund\b",
    r"\bwe\s+guarantee\s+recovery\b",
    r"\byour\s+money\s+will\s+definitely\s+be\s+returned\b",
    r"\byour\s+account\s+will\s+be\s+unblocked\b",
    r"\bthe\s+money\s+will\s+be\s+recovered\b",
]


# Customers must not be directed back to suspicious contacts.
UNSAFE_THIRD_PARTY_PATTERNS = [
    r"\bcontact\s+the\s+caller\b",
    r"\bcall\s+the\s+caller\s+back\b",
    r"\breply\s+to\s+the\s+suspicious\s+(number|message|caller)\b",
    r"\bcontact\s+the\s+suspicious\s+(number|person|caller)\b",
    r"\bfollow\s+the\s+caller's\s+instructions\b",
]


def normalize_text(text: str) -> str:
    """
    Convert text to a normalized lowercase form for safety checking.
    """

    return " ".join(text.lower().split())


def matches_any_pattern(
    text: str,
    patterns: list[str],
) -> bool:
    """
    Return True when the text matches at least one unsafe pattern.
    """

    normalized = normalize_text(text)

    return any(
        re.search(pattern, normalized) is not None
        for pattern in patterns
    )


def has_unsafe_credential_request(text: str) -> bool:
    """
    Detect direct requests for PIN, OTP, password, or full card number.
    """

    return matches_any_pattern(
        text,
        UNSAFE_CREDENTIAL_PATTERNS,
    )


def has_unauthorized_financial_promise(text: str) -> bool:
    """
    Detect promises of refunds, reversals, recovery, or account actions.
    """

    return matches_any_pattern(
        text,
        UNSAFE_FINANCIAL_PROMISE_PATTERNS,
    )


def has_unsafe_third_party_instruction(text: str) -> bool:
    """
    Detect instructions that direct a customer to a suspicious party.
    """

    return matches_any_pattern(
        text,
        UNSAFE_THIRD_PARTY_PATTERNS,
    )


def sanitize_response(
    response: TicketResponse,
) -> TicketResponse:
    """
    Perform a final safety check before a response leaves the API.

    If unsafe language is detected, replace the affected text with a
    conservative fallback rather than allowing unsafe content through.
    """

    safety_fallback_used = False

    customer_reply_is_unsafe = any(
        [
            has_unsafe_credential_request(
                response.customer_reply
            ),
            has_unauthorized_financial_promise(
                response.customer_reply
            ),
            has_unsafe_third_party_instruction(
                response.customer_reply
            ),
        ]
    )

    next_action_is_unsafe = any(
        [
            has_unsafe_credential_request(
                response.recommended_next_action
            ),
            has_unauthorized_financial_promise(
                response.recommended_next_action
            ),
            has_unsafe_third_party_instruction(
                response.recommended_next_action
            ),
        ]
    )

    if customer_reply_is_unsafe:
        response.customer_reply = SAFE_CUSTOMER_REPLY
        safety_fallback_used = True

    if next_action_is_unsafe:
        response.recommended_next_action = SAFE_NEXT_ACTION
        safety_fallback_used = True

    if safety_fallback_used:
        reason_codes = list(response.reason_codes or [])

        if "safety_fallback_applied" not in reason_codes:
            reason_codes.append("safety_fallback_applied")

        response.reason_codes = reason_codes
        response.human_review_required = True

    return response