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
    tags: Optional[str] = None
    model_target: Optional[str] = None


class PromptUpdate(BaseModel):
    """
    What the client sends on PUT /prompts/{id}.

    Every field is Optional with a default of None. This is what makes
    "partial update supported" possible: the client can send just
    {"tags": "new-tag"} and nothing else, and we'll know (in the route)
    to only touch the `tags` column, leaving name/content/etc untouched.
    If every field were required, a partial update would be impossible --
    the client would be forced to resend the entire prompt every time.
    """
    name: Optional[str] = None
    description: Optional[str] = None
    content: Optional[str] = None
    tags: Optional[str] = None
    model_target: Optional[str] = None


class PromptOut(BaseModel):
    """What the server sends back. Includes server-assigned fields
    (id, created_at, updated_at) that the client never provides itself."""
    id: UUID
    name: str
    description: Optional[str] = None
    content: str
    tags: Optional[str] = None
    model_target: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Lets Pydantic build this model directly from a SQLAlchemy ORM
    # object (e.g. PromptOut.model_validate(some_prompt_row)) instead
    # of requiring a plain dict. Without this, returning an ORM object
    # straight from a route would fail.
    model_config = ConfigDict(from_attributes=True)


# ---------------- Week 2: chats and messages ----------------

class MessageOut(BaseModel):
    """A single turn in a chat -- either role='user' or role='assistant'."""
    id: UUID
    chat_id: UUID
    role: str
    content: str
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    created_at: datetime

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


class SummaryOut(BaseModel):
    summary: str
