"""Governed banking tools exposed through FastMCP.

The tool boundaries are inspired by the Microsoft/Azure Samples Multi-Agent
Banking Assistant. Copyright (c) 2024 Azure Samples. Modifications Copyright
(c) 2026 Ashok Chinthakindi. MIT licensed.
"""

from decimal import Decimal

from fastmcp import FastMCP

from .models import PaymentStatus
from .orchestrator import container

mcp = FastMCP("Enterprise Banking MCP Server")


@mcp.tool(name="get_account_summary")
def get_account_summary(user_id: str) -> list[dict]:
    """Get masked balances and payment methods for the authenticated demo user."""

    container.audit_log.record("mcp_account_read", user_id)
    return container.repository.masked_account_summary(user_id)


@mcp.tool(name="get_recent_transactions")
def get_recent_transactions(
    user_id: str,
    account_id: str,
    merchant: str | None = None,
    limit: int = 10,
) -> list[dict]:
    """Get recent synthetic transactions after account ownership validation."""

    container.repository.account(user_id, account_id)
    container.audit_log.record("mcp_transaction_read", user_id, account_id)
    return [
        item.model_dump(mode="json")
        for item in container.repository.transactions(account_id, merchant, limit)
    ]


@mcp.tool(name="get_registered_beneficiaries")
def get_registered_beneficiaries(user_id: str, account_id: str) -> list[dict]:
    """List registered beneficiaries for an owned demo account."""

    container.repository.account(user_id, account_id)
    return [
        item.model_dump(mode="json")
        for item in container.repository.beneficiaries(account_id)
    ]


@mcp.tool(name="create_payment_draft")
def create_payment_draft(
    user_id: str,
    account_id: str,
    payment_method_id: str,
    payee: str,
    amount: float,
    invoice_id: str,
) -> dict:
    """Create a governed draft; this tool never executes the payment."""

    draft = container.payment_service.create_draft(
        user_id=user_id,
        account_id=account_id,
        payment_method_id=payment_method_id,
        payee=payee,
        amount=Decimal(str(amount)),
        invoice_id=invoice_id,
    )
    data = draft.model_dump(mode="json")
    data["requires_human_approval"] = draft.status == PaymentStatus.AWAITING_APPROVAL
    return data


if __name__ == "__main__":
    mcp.run(transport="http", host="0.0.0.0", port=8001)

