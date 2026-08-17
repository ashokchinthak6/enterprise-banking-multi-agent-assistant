"""Banking read services and governed payment workflow."""

import secrets
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from .audit import AuditLog
from .config import Settings
from .data import ACCOUNTS, BENEFICIARIES, PAYMENT_METHODS, TRANSACTIONS
from .models import (
    Account,
    Beneficiary,
    Decision,
    PaymentDraft,
    PaymentMethod,
    PaymentStatus,
    Transaction,
)


def mask_identifier(value: str, visible: int = 4) -> str:
    """Mask an account or card identifier while preserving its last digits."""

    if len(value) <= visible:
        return "•" * len(value)
    return "•" * (len(value) - visible) + value[-visible:]


class BankingRepository:
    """Read-only access layer over synthetic banking records."""

    def accounts_for_user(self, user_id: str) -> list[Account]:
        return [account for account in ACCOUNTS if account.user_id == user_id]

    def account(self, user_id: str, account_id: str) -> Account:
        account = next(
            (
                item
                for item in ACCOUNTS
                if item.user_id == user_id and item.id == account_id
            ),
            None,
        )
        if account is None:
            raise ValueError("Account not found for the authenticated demo user")
        return account

    def payment_methods(self, account_id: str) -> list[PaymentMethod]:
        return [item for item in PAYMENT_METHODS if item.account_id == account_id]

    def payment_method(self, account_id: str, method_id: str) -> PaymentMethod:
        method = next(
            (
                item
                for item in PAYMENT_METHODS
                if item.account_id == account_id and item.id == method_id
            ),
            None,
        )
        if method is None:
            raise ValueError("Payment method is not available for this account")
        return method

    def beneficiaries(self, account_id: str) -> list[Beneficiary]:
        return [item for item in BENEFICIARIES if item.account_id == account_id]

    def transactions(
        self,
        account_id: str,
        merchant: str | None = None,
        limit: int = 10,
    ) -> list[Transaction]:
        rows = [item for item in TRANSACTIONS if item.account_id == account_id]
        if merchant:
            needle = merchant.casefold()
            rows = [item for item in rows if needle in item.merchant.casefold()]
        rows.sort(key=lambda item: item.posted_at, reverse=True)
        return rows[: max(1, min(limit, 50))]

    def masked_account_summary(self, user_id: str) -> list[dict]:
        summaries = []
        for account in self.accounts_for_user(user_id):
            summaries.append(
                {
                    "account_id": account.id,
                    "name": account.name,
                    "account_number": mask_identifier(account.account_number),
                    "currency": account.currency,
                    "balance": account.balance,
                    "available_balance": account.available_balance,
                    "payment_methods": [
                        method.model_dump()
                        for method in self.payment_methods(account.id)
                    ],
                }
            )
        return summaries

    def spending_summary(self, account_id: str) -> dict[str, Decimal]:
        totals: defaultdict[str, Decimal] = defaultdict(lambda: Decimal("0"))
        for transaction in self.transactions(account_id, limit=50):
            if transaction.amount < 0:
                totals[transaction.category] += abs(transaction.amount)
        return dict(sorted(totals.items(), key=lambda item: item[1], reverse=True))


class PaymentService:
    """Two-step payment workflow with policy and human approval controls."""

    def __init__(
        self,
        repository: BankingRepository,
        audit_log: AuditLog,
        settings: Settings,
    ) -> None:
        self.repository = repository
        self.audit_log = audit_log
        self.settings = settings
        self._drafts: dict[str, PaymentDraft] = {}

    def list_drafts(self) -> list[PaymentDraft]:
        return list(reversed(list(self._drafts.values())))

    def get_draft(self, payment_id: str) -> PaymentDraft:
        draft = self._drafts.get(payment_id)
        if draft is None:
            raise ValueError("Payment draft was not found")
        return draft

    def create_draft(
        self,
        *,
        user_id: str,
        account_id: str,
        payment_method_id: str,
        payee: str,
        amount: Decimal,
        invoice_id: str,
    ) -> PaymentDraft:
        account = self.repository.account(user_id, account_id)
        method = self.repository.payment_method(account.id, payment_method_id)
        normalized_invoice = invoice_id.strip().casefold()

        if any(
            item.invoice_id.casefold() == normalized_invoice
            and item.status not in {PaymentStatus.REJECTED}
            for item in self._drafts.values()
        ):
            raise ValueError("A payment already exists for this invoice")

        registered_names = {
            item.name.casefold() for item in self.repository.beneficiaries(account.id)
        }
        if payee.strip().casefold() not in registered_names:
            raise ValueError("Payee is not a registered beneficiary")

        if amount > method.available_amount:
            raise ValueError("Selected payment method has insufficient available funds")

        payment_id = f"pay-{uuid4().hex[:12]}"
        now = datetime.now(UTC)
        if amount > Decimal(str(self.settings.payment_approval_limit)):
            draft = PaymentDraft(
                id=payment_id,
                user_id=user_id,
                account_id=account.id,
                payment_method_id=method.id,
                payee=payee.strip(),
                amount=amount,
                invoice_id=invoice_id.strip(),
                description=f"Payment for invoice {invoice_id.strip()}",
                status=PaymentStatus.BLOCKED,
                created_at=now,
                block_reason="Amount exceeds the demo payment policy limit",
            )
            self._drafts[payment_id] = draft
            self.audit_log.record(
                "payment_blocked",
                user_id,
                payment_id,
                {"reason": draft.block_reason, "amount": str(amount)},
            )
            return draft

        draft = PaymentDraft(
            id=payment_id,
            user_id=user_id,
            account_id=account.id,
            payment_method_id=method.id,
            payee=payee.strip(),
            amount=amount,
            invoice_id=invoice_id.strip(),
            description=f"Payment for invoice {invoice_id.strip()}",
            status=PaymentStatus.AWAITING_APPROVAL,
            approval_token=secrets.token_urlsafe(12),
            created_at=now,
        )
        self._drafts[payment_id] = draft
        self.audit_log.record(
            "payment_draft_created",
            user_id,
            payment_id,
            {"payee": draft.payee, "amount": str(draft.amount)},
        )
        return draft

    def decide(
        self,
        payment_id: str,
        user_id: str,
        decision: Decision,
        approval_token: str,
    ) -> PaymentDraft:
        draft = self.get_draft(payment_id)
        if draft.user_id != user_id:
            raise ValueError("Payment does not belong to the authenticated demo user")
        if draft.status != PaymentStatus.AWAITING_APPROVAL:
            raise ValueError(f"Payment cannot be changed from status {draft.status}")
        if not draft.approval_token or not secrets.compare_digest(
            draft.approval_token, approval_token
        ):
            self.audit_log.record(
                "payment_approval_failed", user_id, payment_id, {"reason": "token"}
            )
            raise ValueError("Approval token is invalid")

        draft.approval_token = None
        if decision == Decision.REJECT:
            draft.status = PaymentStatus.REJECTED
            self.audit_log.record("payment_rejected", user_id, payment_id)
            return draft

        draft.status = PaymentStatus.EXECUTED
        draft.executed_at = datetime.now(UTC)
        self.audit_log.record(
            "payment_executed",
            user_id,
            payment_id,
            {"amount": str(draft.amount), "payee": draft.payee},
        )
        return draft
