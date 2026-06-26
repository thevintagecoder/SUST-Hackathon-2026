import re
from datetime import datetime
from typing import Optional

from app.schemas import (
    CaseType,
    Department,
    EvidenceVerdict,
    Language,
    Severity,
    TicketRequest,
    TicketResponse,
    Transaction,
    TransactionStatus,
    TransactionType,
    UserType,
)


BANGLA_DIGIT_TRANSLATION = str.maketrans(
    "০১২৩৪৫৬৭৮৯",
    "0123456789",
)


def normalize_text(text: str) -> str:
    """
    Converts text to lowercase and changes Bangla digits into English digits.

    Example:
        "আমি ২০০০ টাকা পাঠিয়েছি"
        becomes
        "আমি 2000 টাকা পাঠিয়েছি"
    """
    return text.lower().translate(BANGLA_DIGIT_TRANSLATION)


def contains_any(text: str, keywords: list[str]) -> bool:
    """
    Returns True when at least one keyword appears in the text.
    """
    return any(keyword in text for keyword in keywords)


def extract_numbers(text: str) -> list[float]:
    """
    Extracts numeric values from complaint text.

    Examples:
        "I sent 5000 taka" -> [5000.0]
        "আমি ২০০০ টাকা পাঠিয়েছি" -> [2000.0]
    """
    normalized = normalize_text(text)
    number_strings = re.findall(r"\d+(?:\.\d+)?", normalized)

    return [float(number) for number in number_strings]


def parse_timestamp(timestamp: str) -> Optional[datetime]:
    """
    Safely converts an ISO 8601 timestamp into a datetime object.
    """
    try:
        return datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    except ValueError:
        return None


def find_duplicate_pair(
    transactions: list[Transaction],
) -> Optional[tuple[Transaction, Transaction]]:
    """
    Searches for two completed payments with:

    - the same amount
    - the same counterparty
    - timestamps close together

    The second transaction is treated as the likely duplicate.
    """

    payments = [
        transaction
        for transaction in transactions
        if transaction.type == TransactionType.PAYMENT
        and transaction.status == TransactionStatus.COMPLETED
    ]

    for index, first in enumerate(payments):
        for second in payments[index + 1:]:
            same_amount = first.amount == second.amount
            same_counterparty = first.counterparty == second.counterparty

            if not same_amount or not same_counterparty:
                continue

            first_time = parse_timestamp(first.timestamp)
            second_time = parse_timestamp(second.timestamp)

            if first_time is None or second_time is None:
                continue

            seconds_between = abs(
                (second_time - first_time).total_seconds()
            )

            if seconds_between <= 300:
                if first_time <= second_time:
                    return first, second

                return second, first

    return None


def detect_case_type(ticket: TicketRequest) -> CaseType:
    """
    Determines the complaint category using complaint text,
    user type and transaction information.
    """

    text = normalize_text(ticket.complaint)

    phishing_keywords = [
        "otp",
        "pin",
        "password",
        "verification code",
        "security code",
        "account will be blocked",
        "account blocked",
        "suspicious call",
        "scam",
        "ওটিপি",
        "পিন",
        "পাসওয়ার্ড",
        "পাসওয়ার্ড",
        "একাউন্ট বন্ধ",
        "অ্যাকাউন্ট বন্ধ",
        "otp chaise",
        "otp chay",
        "code dite bolse",
    ]

    duplicate_keywords = [
        "deducted twice",
        "charged twice",
        "paid twice",
        "payment twice",
        "duplicate payment",
        "double charged",
        "twice from my account",
        "দুইবার",
        "দুবার",
        "দুই বার",
        "দু বার",
        "double payment",
    ]

    settlement_keywords = [
        "settlement",
        "settled",
        "merchant settlement",
        "sales have not been settled",
        "সেটেলমেন্ট",
        "সেটেল হয়নি",
        "সেটেল হয়নি",
    ]

    cash_in_keywords = [
        "cash in",
        "cash-in",
        "agent cash",
        "ক্যাশ ইন",
        "ক্যাশইন",
        "এজেন্টের কাছে",
        "agent er kache",
        "cash in korechi",
    ]

    balance_not_received_keywords = [
        "not reflected",
        "not added",
        "balance did not update",
        "balance was not updated",
        "money did not arrive",
        "ব্যালেন্সে টাকা আসেনি",
        "ব্যালেন্সে যোগ হয়নি",
        "ব্যালেন্সে যোগ হয়নি",
        "taka asheni",
        "balance e ashe nai",
    ]

    failed_payment_keywords = [
        "payment failed",
        "transaction failed",
        "app showed failed",
        "failed but",
        "balance deducted",
        "money deducted",
        "deducted but",
        "পেমেন্ট হয়নি",
        "পেমেন্ট হয়নি",
        "টাকা কেটে গেছে",
        "লেনদেন ব্যর্থ",
        "payment hoyni",
        "taka kete geche",
    ]

    wrong_transfer_keywords = [
        "wrong number",
        "wrong person",
        "wrong recipient",
        "sent by mistake",
        "transferred by mistake",
        "typed it wrong",
        "ভুল নম্বর",
        "ভুল নাম্বার",
        "ভুল ব্যক্তিকে",
        "ভুল করে পাঠিয়েছি",
        "ভুল করে পাঠিয়েছি",
        "vul number",
        "vul nambar",
        "vul kore pathaisi",
    ]

    transfer_keywords = [
        "sent",
        "transfer",
        "transferred",
        "পাঠিয়েছি",
        "পাঠিয়েছি",
        "ট্রান্সফার",
        "send korechi",
        "pathaisi",
    ]

    recipient_not_received_keywords = [
        "didn't get it",
        "did not get it",
        "hasn't received",
        "has not received",
        "not received",
        "didn't receive",
        "পায়নি",
        "পায়নি",
        "পাননি",
        "পৌঁছায়নি",
        "পৌঁছায়নি",
        "pay nai",
        "pai nai",
    ]

    refund_keywords = [
        "refund",
        "money back",
        "return my money",
        "changed my mind",
        "রিফান্ড",
        "টাকা ফেরত",
        "refund chai",
        "taka ferot",
    ]

    if contains_any(text, phishing_keywords):
        return CaseType.PHISHING_OR_SOCIAL_ENGINEERING

    if contains_any(text, duplicate_keywords):
        return CaseType.DUPLICATE_PAYMENT

    if (
        ticket.user_type == UserType.MERCHANT
        and contains_any(text, settlement_keywords)
    ):
        return CaseType.MERCHANT_SETTLEMENT_DELAY

    if contains_any(text, settlement_keywords):
        return CaseType.MERCHANT_SETTLEMENT_DELAY

    if (
        contains_any(text, cash_in_keywords)
        and contains_any(text, balance_not_received_keywords)
    ):
        return CaseType.AGENT_CASH_IN_ISSUE

    # Payment failure must be checked before refund request because a
    # failed-payment complaint may also contain the word "refund".
    if contains_any(text, failed_payment_keywords):
        return CaseType.PAYMENT_FAILED

    if contains_any(text, wrong_transfer_keywords):
        return CaseType.WRONG_TRANSFER

    if (
        contains_any(text, transfer_keywords)
        and contains_any(text, recipient_not_received_keywords)
    ):
        return CaseType.WRONG_TRANSFER

    if contains_any(text, refund_keywords):
        return CaseType.REFUND_REQUEST

    return CaseType.OTHER


def expected_transaction_type(
    case_type: CaseType,
) -> Optional[TransactionType]:
    """
    Returns the transaction type normally connected to a case.
    """

    mapping = {
        CaseType.WRONG_TRANSFER: TransactionType.TRANSFER,
        CaseType.PAYMENT_FAILED: TransactionType.PAYMENT,
        CaseType.REFUND_REQUEST: TransactionType.PAYMENT,
        CaseType.DUPLICATE_PAYMENT: TransactionType.PAYMENT,
        CaseType.MERCHANT_SETTLEMENT_DELAY: TransactionType.SETTLEMENT,
        CaseType.AGENT_CASH_IN_ISSUE: TransactionType.CASH_IN,
    }

    return mapping.get(case_type)


def find_explicit_transaction(
    complaint: str,
    transactions: list[Transaction],
) -> Optional[Transaction]:
    """
    Looks for an exact transaction ID written in the complaint.
    """

    complaint_upper = complaint.upper()

    for transaction in transactions:
        if transaction.transaction_id.upper() in complaint_upper:
            return transaction

    return None


def match_transaction(
    ticket: TicketRequest,
    case_type: CaseType,
    duplicate_pair: Optional[tuple[Transaction, Transaction]],
) -> Optional[Transaction]:
    """
    Finds the most likely transaction referred to by the complaint.

    Returns None when:
    - there is no meaningful match
    - multiple transactions are equally plausible
    """

    transactions = ticket.transaction_history

    if not transactions:
        return None

    explicit_match = find_explicit_transaction(
        ticket.complaint,
        transactions,
    )

    if explicit_match is not None:
        return explicit_match

    if (
        case_type == CaseType.DUPLICATE_PAYMENT
        and duplicate_pair is not None
    ):
        # The second transaction is the suspected duplicate.
        return duplicate_pair[1]

    complaint_numbers = extract_numbers(ticket.complaint)
    expected_type = expected_transaction_type(case_type)

    scored_transactions: list[tuple[int, Transaction]] = []

    for transaction in transactions:
        score = 0

        if transaction.amount in complaint_numbers:
            score += 5

        if (
            expected_type is not None
            and transaction.type == expected_type
        ):
            score += 4

        counterparty_digits = re.sub(
            r"\D",
            "",
            transaction.counterparty,
        )

        complaint_digits = re.sub(
            r"\D",
            "",
            normalize_text(ticket.complaint),
        )

        if (
            counterparty_digits
            and len(counterparty_digits) >= 5
            and counterparty_digits in complaint_digits
        ):
            score += 3

        if (
            case_type == CaseType.PAYMENT_FAILED
            and transaction.status == TransactionStatus.FAILED
        ):
            score += 2

        if (
            case_type == CaseType.AGENT_CASH_IN_ISSUE
            and transaction.status == TransactionStatus.PENDING
        ):
            score += 2

        if (
            case_type == CaseType.MERCHANT_SETTLEMENT_DELAY
            and transaction.status == TransactionStatus.PENDING
        ):
            score += 2

        scored_transactions.append((score, transaction))

    scored_transactions.sort(
        key=lambda item: item[0],
        reverse=True,
    )

    highest_score = scored_transactions[0][0]

    # A weak match should not be trusted.
    if highest_score < 4:
        return None

    highest_matches = [
        transaction
        for score, transaction in scored_transactions
        if score == highest_score
    ]

    # Multiple equally strong matches means the evidence is ambiguous.
    if len(highest_matches) > 1:
        return None

    return highest_matches[0]


def determine_evidence_verdict(
    ticket: TicketRequest,
    case_type: CaseType,
    matched_transaction: Optional[Transaction],
    duplicate_pair: Optional[tuple[Transaction, Transaction]],
) -> EvidenceVerdict:
    """
    Compares the complaint against transaction evidence.
    """

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.OTHER:
        return EvidenceVerdict.INSUFFICIENT_DATA

    if (
        case_type == CaseType.DUPLICATE_PAYMENT
        and duplicate_pair is not None
    ):
        return EvidenceVerdict.CONSISTENT

    if matched_transaction is None:
        return EvidenceVerdict.INSUFFICIENT_DATA

    if case_type == CaseType.WRONG_TRANSFER:
        previous_same_recipient = [
            transaction
            for transaction in ticket.transaction_history
            if transaction.transaction_id
            != matched_transaction.transaction_id
            and transaction.type == TransactionType.TRANSFER
            and transaction.counterparty
            == matched_transaction.counterparty
            and transaction.status
            == TransactionStatus.COMPLETED
        ]

        # Several earlier transfers to the same recipient weaken a claim
        # that the recipient was completely accidental.
        if len(previous_same_recipient) >= 2:
            return EvidenceVerdict.INCONSISTENT

        return EvidenceVerdict.CONSISTENT

    if case_type == CaseType.PAYMENT_FAILED:
        if matched_transaction.status in {
            TransactionStatus.FAILED,
            TransactionStatus.PENDING,
        }:
            return EvidenceVerdict.CONSISTENT

        return EvidenceVerdict.INCONSISTENT

    if case_type == CaseType.REFUND_REQUEST:
        return EvidenceVerdict.CONSISTENT

    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        if matched_transaction.status in {
            TransactionStatus.PENDING,
            TransactionStatus.FAILED,
        }:
            return EvidenceVerdict.CONSISTENT

        return EvidenceVerdict.INCONSISTENT

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        if matched_transaction.status == TransactionStatus.PENDING:
            return EvidenceVerdict.CONSISTENT

        return EvidenceVerdict.INCONSISTENT

    return EvidenceVerdict.INSUFFICIENT_DATA


def department_for_case(case_type: CaseType) -> Department:
    """
    Routes the ticket to the correct operational department.
    """

    mapping = {
        CaseType.WRONG_TRANSFER:
            Department.DISPUTE_RESOLUTION,

        CaseType.PAYMENT_FAILED:
            Department.PAYMENTS_OPS,

        CaseType.REFUND_REQUEST:
            Department.CUSTOMER_SUPPORT,

        CaseType.DUPLICATE_PAYMENT:
            Department.PAYMENTS_OPS,

        CaseType.MERCHANT_SETTLEMENT_DELAY:
            Department.MERCHANT_OPERATIONS,

        CaseType.AGENT_CASH_IN_ISSUE:
            Department.AGENT_OPERATIONS,

        CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            Department.FRAUD_RISK,

        CaseType.OTHER:
            Department.CUSTOMER_SUPPORT,
    }

    return mapping[case_type]


def severity_and_review(
    case_type: CaseType,
    evidence_verdict: EvidenceVerdict,
    matched_transaction: Optional[Transaction],
) -> tuple[Severity, bool]:
    """
    Assigns severity and decides whether a human must review the case.
    """

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return Severity.CRITICAL, True

    if case_type == CaseType.DUPLICATE_PAYMENT:
        return Severity.HIGH, True

    if case_type == CaseType.PAYMENT_FAILED:
        human_review = (
            evidence_verdict == EvidenceVerdict.INCONSISTENT
        )
        return Severity.HIGH, human_review

    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return Severity.HIGH, True

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        human_review = (
            evidence_verdict == EvidenceVerdict.INCONSISTENT
        )
        return Severity.MEDIUM, human_review

    if case_type == CaseType.REFUND_REQUEST:
        return Severity.LOW, False

    if case_type == CaseType.WRONG_TRANSFER:
        if evidence_verdict == EvidenceVerdict.CONSISTENT:
            return Severity.HIGH, True

        if evidence_verdict == EvidenceVerdict.INCONSISTENT:
            return Severity.MEDIUM, True

        # Ambiguous transaction: ask for clarification before opening
        # a dispute.
        return Severity.MEDIUM, False

    if (
        matched_transaction is not None
        and matched_transaction.amount >= 50000
    ):
        return Severity.HIGH, True

    return Severity.LOW, False


def build_agent_summary(
    ticket: TicketRequest,
    case_type: CaseType,
    matched_transaction: Optional[Transaction],
    evidence_verdict: EvidenceVerdict,
    duplicate_pair: Optional[tuple[Transaction, Transaction]],
) -> str:
    """
    Produces a concise summary for a support agent.
    """

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return (
            "Customer reports a suspicious communication requesting "
            "sensitive credentials. This is a likely social engineering "
            "attempt and requires fraud-risk escalation."
        )

    if case_type == CaseType.DUPLICATE_PAYMENT:
        if duplicate_pair is not None:
            first, second = duplicate_pair

            return (
                f"Two completed payments of {second.amount:g} BDT to "
                f"{second.counterparty} were found close together "
                f"({first.transaction_id} and "
                f"{second.transaction_id}). The second transaction is "
                f"the likely duplicate."
            )

    if matched_transaction is None:
        if case_type == CaseType.WRONG_TRANSFER:
            return (
                "The customer reports a transfer problem, but multiple "
                "transactions or insufficient details prevent reliable "
                "identification of the relevant transaction."
            )

        return (
            "The complaint does not provide enough evidence to identify "
            "a specific transaction from the supplied history."
        )

    transaction = matched_transaction

    if case_type == CaseType.WRONG_TRANSFER:
        if evidence_verdict == EvidenceVerdict.INCONSISTENT:
            return (
                f"Customer identifies {transaction.transaction_id}, a "
                f"{transaction.amount:g} BDT transfer to "
                f"{transaction.counterparty}, as a wrong transfer. "
                f"Earlier transfers to the same recipient weaken the "
                f"claim."
            )

        return (
            f"Customer reports that {transaction.transaction_id}, a "
            f"{transaction.amount:g} BDT transfer to "
            f"{transaction.counterparty}, may have been sent to the "
            f"wrong recipient."
        )

    if case_type == CaseType.PAYMENT_FAILED:
        return (
            f"Customer reports a failed payment of "
            f"{transaction.amount:g} BDT in "
            f"{transaction.transaction_id}. Recorded transaction "
            f"status is {transaction.status.value}."
        )

    if case_type == CaseType.REFUND_REQUEST:
        return (
            f"Customer requests a refund for completed merchant payment "
            f"{transaction.transaction_id} of "
            f"{transaction.amount:g} BDT."
        )

    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return (
            f"Customer reports that cash-in "
            f"{transaction.transaction_id} of "
            f"{transaction.amount:g} BDT through "
            f"{transaction.counterparty} was not reflected. Recorded "
            f"status is {transaction.status.value}."
        )

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return (
            f"Merchant reports delayed settlement "
            f"{transaction.transaction_id} of "
            f"{transaction.amount:g} BDT. Recorded settlement status is "
            f"{transaction.status.value}."
        )

    return "The ticket was classified for general customer support."


def build_next_action(
    case_type: CaseType,
    matched_transaction: Optional[Transaction],
    evidence_verdict: EvidenceVerdict,
) -> str:
    """
    Produces an operational next step for the support agent.
    """

    transaction_id = (
        matched_transaction.transaction_id
        if matched_transaction is not None
        else "the relevant transaction"
    )

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return (
            "Escalate the report to fraud_risk, record the suspicious "
            "contact details when available, and remind the customer to "
            "use only official support channels."
        )

    if case_type == CaseType.DUPLICATE_PAYMENT:
        return (
            f"Ask payments_ops to verify {transaction_id} with the "
            f"biller. Any reversal should occur only after official "
            f"verification."
        )

    if case_type == CaseType.PAYMENT_FAILED:
        return (
            f"Check the ledger and settlement state for "
            f"{transaction_id}. If an incorrect deduction is confirmed, "
            f"follow the approved reversal process."
        )

    if case_type == CaseType.REFUND_REQUEST:
        return (
            "Explain that refund eligibility depends on the merchant's "
            "policy and guide the customer through the approved refund "
            "request process."
        )

    if case_type == CaseType.AGENT_CASH_IN_ISSUE:
        return (
            f"Route {transaction_id} to agent_operations to confirm the "
            f"cash-in and settlement state with the registered agent."
        )

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        return (
            f"Route {transaction_id} to merchant_operations to verify "
            f"the settlement batch and provide an official status update."
        )

    if case_type == CaseType.WRONG_TRANSFER:
        if matched_transaction is None:
            return (
                "Ask the customer for the recipient number, transaction "
                "ID, amount, or approximate time before opening a dispute."
            )

        if evidence_verdict == EvidenceVerdict.INCONSISTENT:
            return (
                f"Send {transaction_id} for human dispute review and "
                f"verify why the recipient appears in earlier transfers."
            )

        return (
            f"Verify {transaction_id} and begin the approved "
            f"wrong-transfer dispute workflow without promising recovery."
        )

    return (
        "Ask the customer for the transaction ID, amount, approximate "
        "time, and a clear description of what went wrong."
    )


def build_customer_reply(
    ticket: TicketRequest,
    case_type: CaseType,
    matched_transaction: Optional[Transaction],
) -> str:
    """
    Creates a safe customer-facing response.

    The function never asks for PIN, OTP, password or full card details.
    """

    transaction_id = (
        matched_transaction.transaction_id
        if matched_transaction is not None
        else None
    )

    is_bangla = ticket.language == Language.BANGLA

    if is_bangla:
        if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
            return (
                "আমাদের সাথে যোগাযোগ করার জন্য ধন্যবাদ। আমরা কখনোই "
                "আপনার পিন, ওটিপি বা পাসওয়ার্ড চাই না। কারো সাথে এসব "
                "তথ্য শেয়ার করবেন না এবং শুধুমাত্র অফিসিয়াল সাপোর্ট "
                "চ্যানেল ব্যবহার করুন।"
            )

        if case_type == CaseType.AGENT_CASH_IN_ISSUE:
            identifier = transaction_id or "আপনার লেনদেন"

            return (
                f"{identifier} সম্পর্কে আপনার অভিযোগ আমরা পেয়েছি। "
                f"আমাদের এজেন্ট অপারেশন্স দল বিষয়টি যাচাই করবে এবং "
                f"অফিসিয়াল চ্যানেলে আপনাকে জানাবে। কারো সাথে আপনার "
                f"পিন বা ওটিপি শেয়ার করবেন না।"
            )

        return (
            "আপনার অভিযোগ আমরা পেয়েছি। বিষয়টি যাচাই করে অফিসিয়াল "
            "চ্যানেলে আপনাকে জানানো হবে। কারো সাথে আপনার পিন, ওটিপি "
            "বা পাসওয়ার্ড শেয়ার করবেন না।"
        )

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return (
            "Thank you for contacting us before sharing any information. "
            "We never ask for your PIN, OTP, or password. Do not share "
            "these details with anyone, and use only official support "
            "channels."
        )

    if case_type == CaseType.REFUND_REQUEST:
        return (
            "Refund eligibility for a completed merchant payment depends "
            "on the merchant's policy. Please follow the merchant's "
            "official refund process or contact official support for "
            "guidance. Do not share your PIN or OTP with anyone."
        )

    if case_type == CaseType.PAYMENT_FAILED:
        identifier = transaction_id or "the reported transaction"

        return (
            f"We have noted your concern about {identifier}. Our "
            f"payments team will review the transaction, and any eligible "
            f"amount will be returned through official channels. Please "
            f"do not share your PIN or OTP with anyone."
        )

    if case_type == CaseType.DUPLICATE_PAYMENT:
        identifier = transaction_id or "the suspected duplicate payment"

        return (
            f"We have noted the possible duplicate payment involving "
            f"{identifier}. Our payments team will verify it, and any "
            f"eligible amount will be returned through official channels. "
            f"Please do not share your PIN or OTP with anyone."
        )

    if case_type == CaseType.MERCHANT_SETTLEMENT_DELAY:
        identifier = transaction_id or "the reported settlement"

        return (
            f"We have noted your concern about {identifier}. Our merchant "
            f"operations team will verify the settlement batch and update "
            f"you through official channels."
        )

    if case_type == CaseType.WRONG_TRANSFER:
        if transaction_id is None:
            return (
                "We found multiple possible transactions or insufficient "
                "details. Please provide the recipient number, transaction "
                "ID, amount, or approximate time so we can identify the "
                "correct transaction. Do not share your PIN or OTP."
            )

        return (
            f"We have received your concern about transaction "
            f"{transaction_id}. Our dispute team will review it and "
            f"contact you through official channels. Please do not share "
            f"your PIN or OTP with anyone."
        )

    return (
        "Thank you for reaching out. Please provide the transaction ID, "
        "amount, approximate time, and a short description of what went "
        "wrong. Do not share your PIN, OTP, or password with anyone."
    )


def confidence_for_result(
    case_type: CaseType,
    evidence_verdict: EvidenceVerdict,
    matched_transaction: Optional[Transaction],
) -> float:
    """
    Produces a simple confidence score between 0 and 1.
    """

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        return 0.95

    if evidence_verdict == EvidenceVerdict.INCONSISTENT:
        return 0.75

    if (
        evidence_verdict == EvidenceVerdict.CONSISTENT
        and matched_transaction is not None
    ):
        return 0.90

    return 0.60


def reason_codes_for_result(
    case_type: CaseType,
    evidence_verdict: EvidenceVerdict,
    matched_transaction: Optional[Transaction],
) -> list[str]:
    """
    Creates short machine-readable reasons for the decision.
    """

    reasons = [case_type.value, evidence_verdict.value]

    if matched_transaction is not None:
        reasons.append("transaction_match")
    else:
        reasons.append("needs_clarification")

    if case_type == CaseType.PHISHING_OR_SOCIAL_ENGINEERING:
        reasons.append("credential_protection")

    return reasons


def investigate_ticket(ticket: TicketRequest) -> TicketResponse:
    """
    Main investigator pipeline.
    """

    case_type = detect_case_type(ticket)

    duplicate_pair = find_duplicate_pair(
        ticket.transaction_history
    )

    matched_transaction = match_transaction(
        ticket=ticket,
        case_type=case_type,
        duplicate_pair=duplicate_pair,
    )

    evidence_verdict = determine_evidence_verdict(
        ticket=ticket,
        case_type=case_type,
        matched_transaction=matched_transaction,
        duplicate_pair=duplicate_pair,
    )

    department = department_for_case(case_type)

    severity, human_review_required = severity_and_review(
        case_type=case_type,
        evidence_verdict=evidence_verdict,
        matched_transaction=matched_transaction,
    )

    return TicketResponse(
        ticket_id=ticket.ticket_id,
        relevant_transaction_id=(
            matched_transaction.transaction_id
            if matched_transaction is not None
            else None
        ),
        evidence_verdict=evidence_verdict,
        case_type=case_type,
        severity=severity,
        department=department,
        agent_summary=build_agent_summary(
            ticket=ticket,
            case_type=case_type,
            matched_transaction=matched_transaction,
            evidence_verdict=evidence_verdict,
            duplicate_pair=duplicate_pair,
        ),
        recommended_next_action=build_next_action(
            case_type=case_type,
            matched_transaction=matched_transaction,
            evidence_verdict=evidence_verdict,
        ),
        customer_reply=build_customer_reply(
            ticket=ticket,
            case_type=case_type,
            matched_transaction=matched_transaction,
        ),
        human_review_required=human_review_required,
        confidence=confidence_for_result(
            case_type=case_type,
            evidence_verdict=evidence_verdict,
            matched_transaction=matched_transaction,
        ),
        reason_codes=reason_codes_for_result(
            case_type=case_type,
            evidence_verdict=evidence_verdict,
            matched_transaction=matched_transaction,
        ),
    )