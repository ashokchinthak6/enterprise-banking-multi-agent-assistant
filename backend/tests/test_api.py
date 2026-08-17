"""FastAPI integration tests."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_reports_synthetic_mode() -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json()["mode"] == "synthetic-demo"


def test_chat_returns_masked_account_data() -> None:
    response = client.post(
        "/api/chat",
        json={"user_id": "user-1001", "message": "Show my account balance"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["agent"] == "account_agent"
    assert body["data"][0]["account_number"] == "••••••3210"


def test_unknown_account_is_not_exposed() -> None:
    response = client.get(
        "/api/transactions",
        params={"user_id": "user-1001", "account_id": "acct-unknown"},
    )

    assert response.status_code == 404


def test_invoice_extraction_requires_configuration() -> None:
    response = client.post(
        "/api/invoices/extract",
        files={"file": ("invoice.txt", b"synthetic invoice", "text/plain")},
    )

    assert response.status_code == 503
