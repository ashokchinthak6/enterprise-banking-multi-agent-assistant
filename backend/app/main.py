"""FastAPI application for the banking multi-agent demonstration."""

import asyncio
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from .document_intelligence import DocumentIntelligenceService
from .models import ChatRequest, ChatResponse, PaymentDecisionRequest, PaymentDraft
from .orchestrator import container

app = FastAPI(
    title="Enterprise Banking Multi-Agent Assistant",
    version="1.0.0",
    description=(
        "Synthetic banking demo with supervisor routing, MCP tools, payment "
        "approval controls, audit events, and optional Azure integrations."
    ),
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=container.settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

document_service = DocumentIntelligenceService(container.settings)


@app.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "mode": "synthetic-demo",
        "document_intelligence": document_service.enabled,
    }


@app.post("/api/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    try:
        return container.supervisor.route(request.user_id, request.message)
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/accounts")
def accounts(user_id: str = "user-1001") -> list[dict]:
    return container.repository.masked_account_summary(user_id)


@app.get("/api/transactions")
def transactions(
    user_id: str = "user-1001",
    account_id: str = "acct-001",
    merchant: str | None = None,
) -> list[dict]:
    try:
        container.repository.account(user_id, account_id)
        return [
            item.model_dump(mode="json")
            for item in container.repository.transactions(account_id, merchant)
        ]
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error


@app.get("/api/payments", response_model=list[PaymentDraft])
def payments() -> list[PaymentDraft]:
    return container.payment_service.list_drafts()


@app.post("/api/payments/{payment_id}/decision", response_model=PaymentDraft)
def decide_payment(
    payment_id: str,
    request: PaymentDecisionRequest,
    user_id: str = "user-1001",
) -> PaymentDraft:
    try:
        return container.payment_service.decide(
            payment_id,
            user_id,
            request.decision,
            request.approval_token,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error


@app.get("/api/audit")
def audit_events() -> list[dict]:
    return [
        event.model_dump(mode="json")
        for event in container.audit_log.list_events()
    ]


@app.post("/api/invoices/extract")
async def extract_invoice(file: Annotated[UploadFile, File()]) -> dict:
    if not document_service.enabled:
        raise HTTPException(
            status_code=503,
            detail="Azure AI Document Intelligence is not configured",
        )
    content = await file.read()
    if len(content) > 5 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Invoice file exceeds 5 MB")
    try:
        result = await asyncio.to_thread(document_service.extract_invoice, content)
        container.audit_log.record(
            "invoice_extracted",
            container.settings.demo_user_id,
            details={"filename": file.filename, "review_required": True},
        )
        return result
    except (RuntimeError, ValueError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
