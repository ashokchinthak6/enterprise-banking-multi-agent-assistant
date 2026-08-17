"""Shared API and domain models."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator


class AgentName(StrEnum):
    SUPERVISOR = "supervisor"
    ACCOUNT = "account_agent"
    TRANSACTION = "transaction_agent"
    PAYMENT = "payment_agent"
    RISK = "risk_agent"


class PaymentStatus(StrEnum):
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    REJECTED = "rejected"
    BLOCKED = "blocked"
    EXECUTED = "executed"


class Decision(StrEnum):
    APPROVE = "approve"
    REJECT = "reject"


class Account(BaseModel):
    id: str
    user_id: str
    name: str
    account_number: str
    currency: str = "USD"
    balance: Decimal
    available_balance: Decimal


class PaymentMethod(BaseModel):
    id: str
    account_id: str
    kind: str
    label: str
    available_amount: Decimal


class Beneficiary(BaseModel):
    id: str
    account_id: str
    name: str
    bank_code: str


class Transaction(BaseModel):
    id: str
    account_id: str
    posted_at: datetime
    merchant: str
    amount: Decimal
    category: str
    status: str = "posted"


class ChatRequest(BaseModel):
    message: str = Field(min_length=2, max_length=2000)
    user_id: str = "user-1001"

    @field_validator("message")
    @classmethod
    def strip_message(cls, value: str) -> str:
        return value.strip()


class PaymentDraft(BaseModel):
    id: str
    user_id: str
    account_id: str
    payment_method_id: str
    payee: str
    amount: Decimal = Field(gt=0)
    invoice_id: str
    description: str
    status: PaymentStatus
    approval_token: str | None = None
    created_at: datetime
    executed_at: datetime | None = None
    block_reason: str | None = None


class PaymentDecisionRequest(BaseModel):
    decision: Decision
    approval_token: str


class ChatResponse(BaseModel):
    agent: AgentName
    message: str
    data: dict | list | None = None
    approval_required: bool = False
    payment_draft: PaymentDraft | None = None


class AuditEvent(BaseModel):
    id: str
    event_type: str
    actor: str
    resource_id: str | None = None
    details: dict = Field(default_factory=dict)
    occurred_at: datetime

