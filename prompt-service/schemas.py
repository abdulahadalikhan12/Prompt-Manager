from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class PromptCreate(BaseModel):
    """What the client sends on POST /prompts. name and content are
    required -- you can't have a prompt with no text and no label."""
    name: str
    description: Optional[str] = None
    content: str


class PromptUpdate(BaseModel):
    """
    What the client sends on PUT /prompts/{id}. Every field optional,
    so partial updates work via exclude_unset in the service layer.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None


class PromptOut(BaseModel):
    """What the server sends back. Includes server-assigned fields
    (id, created_at, updated_at) that the client never provides itself."""
    id: UUID
    name: str
    description: Optional[str] = None
    content: str
    created_at: datetime
    updated_at: datetime

    # Lets Pydantic build this model directly from a SQLAlchemy ORM
    # object (e.g. PromptOut.model_validate(some_prompt_row)) instead
    # of requiring a plain dict. Without this, returning an ORM object
    # straight from a route would fail.
    model_config = ConfigDict(from_attributes=True)


# ---------------- Week 2: chats and messages ----------------

class MessageOut(BaseModel):
    """A single turn in a chat -- either role='user' or role='assistant'.
    The three token fields let the frontend show a System/Input/Output
    breakdown without further math (input = prompt_tokens - system_tokens)."""
    id: UUID
    chat_id: UUID
    role: str
    content: str
    system_tokens: int
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatDocumentOut(BaseModel):
    id: UUID
    chat_id: UUID
    document_id: UUID
    filename: str
    attached_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatOut(BaseModel):
    """A full chat, including every message in order. This is what
    GET /chats/{chat_id} returns -- the whole conversation at once,
    not paginated, since a chat reviewed by review-service needs the
    complete history in a single snapshot."""
    id: UUID
    prompt_id: UUID
    title: Optional[str] = None
    total_tokens: int
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[MessageOut] = []
    documents: list[ChatDocumentOut] = []

    model_config = ConfigDict(from_attributes=True)


class ChatSummary(BaseModel):
    """Lightweight chat representation for list views (GET /chats and
    the frontend's history page) -- omits the full message list so
    listing many chats doesn't mean transferring every message in
    every one of them over the wire."""
    id: UUID
    prompt_id: UUID
    title: Optional[str] = None
    total_tokens: int
    summary: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ExecuteRequest(BaseModel):
    """Body for POST /prompts/{id}/execute. Everything is optional --
    the simplest possible call is an empty body, just {}'."""
    model: Optional[str] = None


class FollowUpRequest(BaseModel):
    """Body for POST /chats/{chat_id}/messages -- the user's next
    message in an already-open chat."""
    content: str
    model: Optional[str] = None


class DocumentAttachment(BaseModel):
    """One document to attach to a chat. Carries the metadata + text
    that the frontend already received from document-service on upload,
    so prompt-service does NOT have to call back into document-service --
    same idea as why review-service snapshots a chat verbatim instead
    of re-fetching it during summary calculations."""
    document_id: UUID
    filename: str
    extracted_text: str


class AttachDocumentRequest(BaseModel):
    """Body for POST /chats/{chat_id}/documents. Reused inside
    StartChatRequest as a list to seed a brand-new chat with attachments."""
    document_id: UUID
    filename: str
    extracted_text: str


class StartChatRequest(BaseModel):
    """Body for POST /chats -- the user's first message in a brand-new
    chat. The library/picker step is gone; sending the first message is
    what creates both a prompt row (auto-named from the content) AND the
    chat that hangs off it. Attachments are optional -- if present, they
    are written into chat_documents before the first LLM call so the
    system prompt for that very first turn already includes them."""
    content: str
    model: Optional[str] = None
    attachments: list[DocumentAttachment] = []


class SummaryOut(BaseModel):
    summary: str
