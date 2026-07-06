from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from database import get_db
from schemas import (
    AttachDocumentRequest,
    ChatDocumentOut,
    ChatOut,
    ChatSummary,
    DocumentAttachment,
    ExecuteRequest,
    FollowUpRequest,
    StartChatRequest,
    SummaryOut,
)
from services.chat_service import ChatService

router = APIRouter(tags=["chats"])


def get_chat_service(request: Request, db: Session = Depends(get_db)) -> ChatService:
    """
    Same chained-dependency pattern as get_prompt_service, but this one
    also needs the shared httpx.AsyncClient off app.state (set up in
    main.py's lifespan) since ChatService makes outbound calls to
    llm-service.
    """
    return ChatService(db, request.app.state.http_client)


@router.post("/chats", response_model=ChatOut, status_code=201)
async def start_chat(payload: StartChatRequest, service: ChatService = Depends(get_chat_service)):
    """Start a new chat directly from a first message -- no stored
    prompt picker, the message itself becomes the auto-created prompt.
    Optional attachments are written into chat_documents before the
    first LLM call so they're already in the system prompt for turn 1."""
    return await service.start_chat(
        payload.content, model=payload.model, attachments=payload.attachments,
    )


@router.get("/chats/{chat_id}/documents", response_model=list[ChatDocumentOut])
def list_chat_documents(chat_id: UUID, service: ChatService = Depends(get_chat_service)):
    return service.list_documents(chat_id)


@router.post("/chats/{chat_id}/documents", response_model=ChatDocumentOut, status_code=201)
def attach_chat_document(
    chat_id: UUID,
    payload: AttachDocumentRequest,
    service: ChatService = Depends(get_chat_service),
):
    attachment = DocumentAttachment(**payload.model_dump())
    return service.attach_document(chat_id, attachment)


@router.delete("/chats/{chat_id}/documents/{document_id}", status_code=204)
def detach_chat_document(
    chat_id: UUID,
    document_id: UUID,
    service: ChatService = Depends(get_chat_service),
):
    if not service.detach_document(chat_id, document_id):
        raise HTTPException(status_code=404, detail="Attachment not found")
    return None


@router.post("/prompts/{prompt_id}/execute", response_model=ChatOut, status_code=201)
async def execute_prompt(prompt_id: UUID, payload: ExecuteRequest, service: ChatService = Depends(get_chat_service)):
    return await service.execute_prompt(prompt_id, model=payload.model)


@router.post("/chats/{chat_id}/messages", response_model=ChatOut)
async def follow_up(chat_id: UUID, payload: FollowUpRequest, service: ChatService = Depends(get_chat_service)):
    return await service.follow_up(chat_id, payload.content, model=payload.model)


@router.get("/chats", response_model=list[ChatSummary])
def list_chats(prompt_id: Optional[UUID] = Query(default=None), service: ChatService = Depends(get_chat_service)):
    return service.list_chats(prompt_id=prompt_id)


@router.get("/chats/{chat_id}", response_model=ChatOut)
def get_chat(chat_id: UUID, service: ChatService = Depends(get_chat_service)):
    chat = service.get_chat(chat_id)
    if chat is None:
        raise HTTPException(status_code=404, detail="Chat not found")
    return chat


@router.post("/chats/{chat_id}/summary", response_model=SummaryOut)
async def summarize_chat(chat_id: UUID, service: ChatService = Depends(get_chat_service)):
    summary = await service.summarize_chat(chat_id)
    return SummaryOut(summary=summary)


@router.delete("/chats/{chat_id}", status_code=204)
def delete_chat(chat_id: UUID, service: ChatService = Depends(get_chat_service)):
    deleted = service.delete_chat(chat_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Chat not found")
    return None
