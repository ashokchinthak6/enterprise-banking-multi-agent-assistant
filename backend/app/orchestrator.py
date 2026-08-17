"""Dependency assembly for the local multi-agent workflow."""

from .agents import (
    AccountAgent,
    PaymentAgent,
    RiskAgent,
    SupervisorAgent,
    TransactionAgent,
)
from .audit import AuditLog
from .config import get_settings
from .services import BankingRepository, PaymentService


class ApplicationContainer:
    """Small dependency container shared by FastAPI and tests."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self.repository = BankingRepository()
        self.audit_log = AuditLog()
        self.payment_service = PaymentService(
            self.repository, self.audit_log, self.settings
        )
        self.account_agent = AccountAgent(self.repository)
        self.transaction_agent = TransactionAgent(self.repository)
        self.payment_agent = PaymentAgent(self.repository, self.payment_service)
        self.risk_agent = RiskAgent(self.repository)
        self.supervisor = SupervisorAgent(
            self.account_agent,
            self.transaction_agent,
            self.payment_agent,
            self.risk_agent,
            self.audit_log,
        )


container = ApplicationContainer()

