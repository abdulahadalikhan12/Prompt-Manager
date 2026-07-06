"""
All document business logic. Router stays thin -- it only converts
HTTP-layer concerns (UploadFile, HTTPException) to/from plain Python.
"""
from typing import Optional
from uuid import UUID

from fastapi import HTTPException

from core.config import settings
from extractor import ExtractionError, extract
from storage import DocumentStorage


ALLOWED_KINDS = {
    "application/pdf": "pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}


class DocumentService:
    """
    Owns the upload-extract-save flow. Synchronous on purpose: there are
    no outbound HTTP calls here, just local disk I/O and CPU-bound text
    extraction, so async would only add ceremony without payoff. The
    router still exposes async endpoints to keep FastAPI's event loop
    happy, but it just awaits a `run_in_threadpool`-friendly path.
    """

    def __init__(self, storage: DocumentStorage):
        self.storage = storage

    def upload(self, raw: bytes, filename: str, content_type: str) -> dict:
        if len(raw) > settings.MAX_UPLOAD_BYTES:
            raise HTTPException(
                status_code=413,
                detail=f"File exceeds the {settings.MAX_UPLOAD_BYTES} byte upload limit.",
            )

        kind = self._classify(filename, content_type)
        try:
            text = extract(raw, kind)
        except ExtractionError as e:
            raise HTTPException(status_code=422, detail=str(e))

        return self.storage.save(raw, filename=filename, kind=kind, text=text)

    def get(self, doc_id: UUID) -> Optional[dict]:
        return self.storage.get(str(doc_id))

    def list_all(self) -> list[dict]:
        return self.storage.list_all()

    def delete(self, doc_id: UUID) -> bool:
        return self.storage.delete(str(doc_id))

    def _classify(self, filename: str, content_type: str) -> str:
        """Trust the MIME type first, fall back to extension. Some
        browsers send 'application/octet-stream' for DOCX, so the
        extension check is a real safety net, not paranoia."""
        if content_type in ALLOWED_KINDS:
            return ALLOWED_KINDS[content_type]

        lower = (filename or "").lower()
        if lower.endswith(".pdf"):
            return "pdf"
        if lower.endswith(".docx"):
            return "docx"

        raise HTTPException(
            status_code=415,
            detail="Only PDF and DOCX files are supported.",
        )
