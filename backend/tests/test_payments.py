"""Tests for governed payment controls and data masking."""

from decimal import Decimal

import pytest

from app.audit import AuditLog
from app.config import Settings
from app.models import Decision, PaymentStatus
from app.services import BankingRepository, PaymentService, mask_identifier


@pytest.fixture
def payment_service() -> PaymentService:
    return PaymentService(
        BankingRepository(),
        AuditLog(),
        Settings(payment_approval_limit=5000),
    )


def create_draft(
    service: PaymentService,
    *,
    amount: str = "125.40",
    invoice_id: str = "INV-TEST-201",
):
    return service.create_draft(
        user_id="user-1001",
        account_id="acct-001",
        payment_method_id="method-bank-001",
        payee="Contoso Utilities",
        amount=Decimal(amount),
        invoice_id=invoice_id,
    )


def test_account_identifiers_are_masked() -> None:
    summary = BankingRepository().masked_account_summary("user-1001")[0]

    assert summary["account_number"] == "••••••3210"
    assert "987654" not in summary["account_number"]
    assert mask_identifier("1234") == "••••"


def test_payment_requires_valid_human_approval(
    payment_service: PaymentService,
) -> None:
    draft = create_draft(payment_service)

    with pytest.raises(ValueError, match="invalid"):
        payment_service.decide(draft.id, draft.user_id, Decision.APPROVE, "wrong")

    approved = payment_service.decide(
        draft.id,
        draft.user_id,
        Decision.APPROVE,
        str(draft.approval_token),
    )

    assert approved.status == PaymentStatus.EXECUTED
    assert approved.approval_token is None
    assert approved.executed_at is not None


def test_duplicate_invoice_is_rejected(payment_service: PaymentService) -> None:
    create_draft(payment_service, invoice_id="INV-DUPLICATE")

    with pytest.raises(ValueError, match="already exists"):
        create_draft(payment_service, invoice_id="inv-duplicate")


def test_high_value_payment_is_blocked(payment_service: PaymentService) -> None:
    draft = create_draft(
        payment_service,
        amount="6000",
        invoice_id="INV-HIGH-VALUE",
    )

    assert draft.status == PaymentStatus.BLOCKED
    assert draft.approval_token is None
    assert draft.block_reason
