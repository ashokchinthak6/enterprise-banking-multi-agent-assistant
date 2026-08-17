"""Synthetic banking data used by the local demonstration."""

from datetime import UTC, datetime, timedelta
from decimal import Decimal

from .models import Account, Beneficiary, PaymentMethod, Transaction

NOW = datetime.now(UTC)

ACCOUNTS = [
    Account(
        id="acct-001",
        user_id="user-1001",
        name="Everyday Checking",
        account_number="9876543210",
        balance=Decimal("8432.18"),
        available_balance=Decimal("7932.18"),
    )
]

PAYMENT_METHODS = [
    PaymentMethod(
        id="method-bank-001",
        account_id="acct-001",
        kind="bank_transfer",
        label="Everyday Checking ••••3210",
        available_amount=Decimal("7932.18"),
    ),
    PaymentMethod(
        id="method-card-001",
        account_id="acct-001",
        kind="credit_card",
        label="Rewards Visa ••••4821",
        available_amount=Decimal("4200.00"),
    ),
]

BENEFICIARIES = [
    Beneficiary(
        id="beneficiary-001",
        account_id="acct-001",
        name="Contoso Utilities",
        bank_code="BANK-US-001",
    ),
    Beneficiary(
        id="beneficiary-002",
        account_id="acct-001",
        name="Northwind Insurance",
        bank_code="BANK-US-014",
    ),
]

TRANSACTIONS = [
    Transaction(
        id="txn-001",
        account_id="acct-001",
        posted_at=NOW - timedelta(days=1),
        merchant="Contoso Utilities",
        amount=Decimal("-118.42"),
        category="utilities",
    ),
    Transaction(
        id="txn-002",
        account_id="acct-001",
        posted_at=NOW - timedelta(days=2),
        merchant="Fabrikam Market",
        amount=Decimal("-86.17"),
        category="groceries",
    ),
    Transaction(
        id="txn-003",
        account_id="acct-001",
        posted_at=NOW - timedelta(days=4),
        merchant="Payroll Deposit",
        amount=Decimal("3250.00"),
        category="income",
    ),
    Transaction(
        id="txn-004",
        account_id="acct-001",
        posted_at=NOW - timedelta(days=5),
        merchant="City Transit",
        amount=Decimal("-42.50"),
        category="transportation",
    ),
    Transaction(
        id="txn-005",
        account_id="acct-001",
        posted_at=NOW - timedelta(days=7),
        merchant="Northwind Insurance",
        amount=Decimal("-164.25"),
        category="insurance",
    ),
]

