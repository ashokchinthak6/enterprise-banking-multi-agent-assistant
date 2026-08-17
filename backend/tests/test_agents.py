"""Tests for supervisor routing and specialist behavior."""

from app.models import AgentName
from app.orchestrator import ApplicationContainer


def test_supervisor_routes_supported_intents() -> None:
    container = ApplicationContainer()

    assert (
        container.supervisor.route("user-1001", "Show my account balance").agent
        == AgentName.ACCOUNT
    )
    assert (
        container.supervisor.route("user-1001", "Show transaction history").agent
        == AgentName.TRANSACTION
    )
    assert (
        container.supervisor.route("user-1001", "Check for suspicious activity").agent
        == AgentName.RISK
    )


def test_payment_agent_creates_approval_draft() -> None:
    container = ApplicationContainer()

    response = container.supervisor.route(
        "user-1001",
        "Pay Contoso Utilities $125.40 for invoice INV-TEST-101",
    )

    assert response.agent == AgentName.PAYMENT
    assert response.approval_required is True
    assert response.payment_draft is not None
    assert response.payment_draft.approval_token


def test_unknown_intent_stays_with_supervisor() -> None:
    container = ApplicationContainer()

    response = container.supervisor.route("user-1001", "Tell me a joke")

    assert response.agent == AgentName.SUPERVISOR
    assert response.approval_required is False
