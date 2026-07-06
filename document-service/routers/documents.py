from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.concurrency import run_in_threadpool

from core.config import settings
from schemas import DocumentOut, DocumentText
from services.document_service import DocumentService
from storage import DocumentStorage

router = APIRouter(prefix="/documents", tags=["documents"])


def get_document_service() -> DocumentService:
    """One service instance per request -- both the storage and the
    service itself are cheap to construct (no DB session, no client
    state), so we skip the FastAPI-level singleton dance."""
    storage = DocumentStorage(root_dir=settings.DATA_DIR)
    return DocumentService(storage)


@router.post("", response_model=DocumentOut, status_code=201)
async def upload_document(
    file: UploadFile = File(...),
    service: DocumentService = Depends(get_document_service),
):
    """
    Endpoint is async so FastAPI doesn't block the loop while uvicorn
    drains the request body off the socket. The CPU-bound parse itself
    is run inside run_in_threadpool so heavy PDFs don't stall other
    concurrent uploads.
    """
    raw = await file.read()
    meta = await run_in_threadpool(
        service.upload, raw, file.filename or "unnamed", file.content_type or "",
    )
    return meta


@router.get("", response_model=list[DocumentOut])
def list_documents(service: DocumentService = Depends(get_document_service)):
    return service.list_all()


@router.get("/{document_id}", response_model=DocumentOut)
def get_document(document_id: UUID, service: DocumentService = Depends(get_document_service)):
    doc = service.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return doc


@router.get("/{document_id}/text", response_model=DocumentText)
def get_document_text(document_id: UUID, service: DocumentService = Depends(get_document_service)):
    """Heavy field on its own endpoint so the index view stays light."""
    doc = service.get(document_id)
    if doc is None:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentText(id=doc["id"], text=doc["text"])


@router.delete("/{document_id}", status_code=204)
def delete_document(document_id: UUID, service: DocumentService = Depends(get_document_service)):
    if not service.delete(document_id):
        raise HTTPException(status_code=404, detail="Document not found")
    return None
