"""Optional Azure AI Document Intelligence invoice adapter."""

from typing import Any

from .config import Settings


class DocumentIntelligenceService:
    """Extract selected prebuilt-invoice fields when Azure is configured."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    @property
    def enabled(self) -> bool:
        return bool(self.settings.azure_document_intelligence_endpoint)

    def extract_invoice(self, content: bytes) -> dict[str, Any]:
        if not self.enabled:
            raise RuntimeError("Azure AI Document Intelligence is not configured")
        if not content:
            raise ValueError("Invoice file is empty")

        try:
            from azure.ai.documentintelligence import DocumentIntelligenceClient
            from azure.core.credentials import AzureKeyCredential
            from azure.identity import DefaultAzureCredential
        except ImportError as error:
            raise RuntimeError(
                "Install the 'azure' project extra to enable invoice extraction"
            ) from error

        credential = (
            AzureKeyCredential(self.settings.azure_document_intelligence_api_key)
            if self.settings.azure_document_intelligence_api_key
            else DefaultAzureCredential()
        )
        client = DocumentIntelligenceClient(
            endpoint=str(self.settings.azure_document_intelligence_endpoint),
            credential=credential,
        )
        poller = client.begin_analyze_document("prebuilt-invoice", body=content)
        result = poller.result()
        if not result.documents:
            return {"fields": {}, "confidence": 0, "review_required": True}

        fields = result.documents[0].fields or {}

        def field_value(name: str) -> Any:
            field = fields.get(name)
            if not field:
                return None
            return getattr(field, "value", None) or getattr(field, "content", None)

        confidences = [
            float(field.confidence)
            for field in fields.values()
            if getattr(field, "confidence", None) is not None
        ]
        confidence = round(sum(confidences) / len(confidences), 3) if confidences else 0
        return {
            "fields": {
                "invoice_id": field_value("InvoiceId"),
                "vendor_name": field_value("VendorName"),
                "invoice_total": str(field_value("InvoiceTotal") or ""),
                "invoice_date": str(field_value("InvoiceDate") or ""),
                "due_date": str(field_value("DueDate") or ""),
            },
            "confidence": confidence,
            "review_required": True,
        }

