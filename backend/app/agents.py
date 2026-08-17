"""Deterministic demo agents and optional Microsoft Agent Framework adapter.

The supervisor and specialist separation is inspired by the Microsoft/Azure
Samples Multi-Agent Banking Assistant. Copyright (c) 2024 Azure Samples.
Modifications Copyright (c) 2026 Ashok Chinthakindi. MIT licensed.
"""

import re
from decimal import Decimal, InvalidOperation

from .audit import AuditLog
from .config import Settings
from .models import AgentName, ChatResponse, PaymentStatus
from .services import BankingRepository, PaymentService


class AccountAgent:
    name = AgentName.ACCOUNT

    def __init__(self, repository: BankingRepository) -> None:
        self.repository = repository

    def handle(self, user_id: str, _message: str) -> ChatResponse:
        summaries = self.repository.masked_account_summary(user_id)
        return ChatResponse(
            agent=self.name,
            message=(
                "Here is the synthetic account summary. Identifiers are masked, "
                "and no production banking system is connected."
            ),
            data=summaries,
        )


class TransactionAgent:
    name = AgentName.TRANSACTION

    def __init__(self, repository: BankingRepository) -> None:
        self.repository = repository

    def handle(self, user_id: str, message: str) -> ChatResponse:
        accounts = self.repository.accounts_for_user(user_id)
        if not accounts:
            return ChatResponse(agent=self.name, message="No demo account was found.")

        account = accounts[0]
        merchant = self._merchant_filter(message)
        rows = self.repository.transactions(account.id, merchant=merchant)
        summary = self.repository.spending_summary(account.id)
        return ChatResponse(
            agent=self.name,
            message="I found the most recent matching synthetic transactions.",
            data={
                "transactions": [row.model_dump(mode="json") for row in rows],
                "spending_by_category": {
                    category: str(amount) for category, amount in summary.items()
                },
                "merchant_filter": merchant,
            },
        )

    @staticmethod
    def _merchant_filter(message: str) -> str | None:
        match = re.search(r"(?:from|merchant)\s+([\w &'.-]+)", message, re.I)
        return match.group(1).strip(" .") if match else None


class RiskAgent:
    name = AgentName.RISK

    def __init__(self, repository: BankingRepository) -> None:
        self.repository = repository

    def handle(self, user_id: str, _message: str) -> ChatResponse:
        accounts = self.repository.accounts_for_user(user_id)
        if not accounts:
            return ChatResponse(agent=self.name, message="No demo account was found.")

        rows = self.repository.transactions(accounts[0].id, limit=20)
        flags = [
            {
                "transaction_id": row.id,
                "reason": "Large outbound transaction requires review",
                "amount": str(row.amount),
            }
            for row in rows
            if row.amount < Decimal("-2000")
        ]
        return ChatResponse(
            agent=self.name,
            message=(
                "The deterministic demo policy completed its review. This is "
                "not a bank fraud determination."
            ),
            data={"risk_flags": flags, "reviewed_transactions": len(rows)},
        )


class PaymentAgent:
    name = AgentName.PAYMENT

    def __init__(
        self, repository: BankingRepository, payment_service: PaymentService
    ) -> None:
        self.repository = repository
        self.payment_service = payment_service

    def handle(self, user_id: str, message: str) -> ChatResponse:
        parsed = self._parse_payment(message)
        missing = [key for key, value in parsed.items() if value is None]
        if missing:
            return ChatResponse(
                agent=self.name,
                message=(
                    "I need the payee, dollar amount, and invoice ID before I can "
                    f"create a payment draft. Missing: {', '.join(missing)}."
                ),
                data={"example": "Pay Contoso Utilities $125.40 for invoice INV-2048"},
            )

        accounts = self.repository.accounts_for_user(user_id)
        if not accounts:
            return ChatResponse(agent=self.name, message="No demo account was found.")
        account = accounts[0]
        methods = self.repository.payment_methods(account.id)
        if not methods:
            return ChatResponse(
                agent=self.name,
                message="No payment method is available.",
            )

        draft = self.payment_service.create_draft(
            user_id=user_id,
            account_id=account.id,
            payment_method_id=methods[0].id,
            payee=str(parsed["payee"]),
            amount=Decimal(str(parsed["amount"])),
            invoice_id=str(parsed["invoice_id"]),
        )

        if draft.status == PaymentStatus.BLOCKED:
            return ChatResponse(
                agent=self.name,
                message=f"The payment was blocked: {draft.block_reason}.",
                data={
                    "policy_limit": (
                        self.payment_service.settings.payment_approval_limit
                    )
                },
                payment_draft=draft,
            )

        return ChatResponse(
            agent=self.name,
            message=(
                "I created a payment draft. Review every field before approving. "
                "The payment has not been executed."
            ),
            approval_required=True,
            payment_draft=draft,
        )

    @staticmethod
    def _parse_payment(message: str) -> dict[str, str | Decimal | None]:
        amount_match = re.search(r"(?:\$|usd\s*)(\d+(?:\.\d{1,2})?)", message, re.I)
        invoice_match = re.search(
            r"invoice(?:\s*(?:id|number))?\s*[:#-]?\s*([a-z0-9-]+)",
            message,
            re.I,
        )
        payee_match = re.search(
            r"(?:pay|to)\s+([a-z][\w &'\.-]*?)(?=\s+\$|\s+usd|\s+for\s+invoice|$)",
            message,
            re.I,
        )
        try:
            amount = Decimal(amount_match.group(1)) if amount_match else None
        except InvalidOperation:
            amount = None
        return {
            "payee": payee_match.group(1).strip() if payee_match else None,
            "amount": amount,
            "invoice_id": invoice_match.group(1) if invoice_match else None,
        }


class SupervisorAgent:
    """Routes a request to exactly one least-privileged specialist."""

    name = AgentName.SUPERVISOR

    def __init__(
        self,
        account_agent: AccountAgent,
        transaction_agent: TransactionAgent,
        payment_agent: PaymentAgent,
        risk_agent: RiskAgent,
        audit_log: AuditLog,
    ) -> None:
        self.account_agent = account_agent
        self.transaction_agent = transaction_agent
        self.payment_agent = payment_agent
        self.risk_agent = risk_agent
        self.audit_log = audit_log

    def route(self, user_id: str, message: str) -> ChatResponse:
        normalized = message.casefold()
        if any(word in normalized for word in ("fraud", "suspicious", "risk")):
            agent = self.risk_agent
        elif any(word in normalized for word in ("pay ", "payment", "invoice", "bill")):
            agent = self.payment_agent
        elif any(
            word in normalized
            for word in ("transaction", "spending", "merchant", "history")
        ):
            agent = self.transaction_agent
        elif any(
            word in normalized
            for word in ("balance", "account", "card", "beneficiary", "funds")
        ):
            agent = self.account_agent
        else:
            return ChatResponse(
                agent=self.name,
                message=(
                    "I can help with demo account balances, transactions, payment "
                    "drafts, invoices, and risk reviews."
                ),
            )

        self.audit_log.record(
            "agent_routed",
            user_id,
            details={"agent": agent.name.value},
        )
        return agent.handle(user_id, message)


class AzureAgentFactory:
    """Build Microsoft Agent Framework specialists when Azure is configured."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    async def build(self) -> dict[str, object]:
        if not self.settings.azure_openai_endpoint:
            raise RuntimeError("AZURE_OPENAI_ENDPOINT is not configured")

        try:
            from agent_framework import Agent, MCPStreamableHTTPTool
            from agent_framework.openai import OpenAIChatCompletionClient
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise RuntimeError(
                "Install the 'azure' project extra to enable cloud agents"
            ) from error

        client = OpenAIChatCompletionClient(
            credential=DefaultAzureCredential(),
            azure_endpoint=self.settings.azure_openai_endpoint,
            model=self.settings.azure_openai_deployment,
        )
        mcp_tool = MCPStreamableHTTPTool(
            name="Governed Banking MCP Tools",
            url=self.settings.mcp_server_url,
        )
        await mcp_tool.connect()

        shared_rules = (
            "Use only the provided MCP tools. Never invent banking data. Never "
            "execute a payment without an explicit human approval event."
        )
        return {
            "account": Agent(
                client=client,
                name="AccountAgent",
                instructions=f"Answer account questions. {shared_rules}",
                tools=[mcp_tool],
            ),
            "transaction": Agent(
                client=client,
                name="TransactionAgent",
                instructions=f"Analyze transaction history. {shared_rules}",
                tools=[mcp_tool],
            ),
            "payment": Agent(
                client=client,
                name="PaymentAgent",
                instructions=f"Prepare governed payment drafts. {shared_rules}",
                tools=[mcp_tool],
            ),
        }
