from typing import Optional, Literal, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReviewCreate(BaseModel):
    """
    What the client sends on POST /reviews.

    target_type selects what's being reviewed and which id field is
    required: a stored prompt, a full chat, or a single user message
    inside a chat. Exactly one id field per target_type is enforced
    by the model_validator below, before any business logic runs.

    "message" reviews require BOTH chat_id and message_id, because
    review-service can only locate a message by fetching its parent
    chat from prompt-service (there is no GET /messages/{id} endpoint --
    keeping the prompt-service surface area minimal).
    """
    target_type: Literal["prompt", "chat", "message"] = "prompt"
    prompt_id: Optional[UUID] = None
    chat_id: Optional[UUID] = None
    message_id: Optional[UUID] = None
    reviewer_name: str
    score: int = Field(ge=1, le=5)
    feedback: str

    @model_validator(mode="after")
    def check_target_matches_id(self):
        if self.target_type == "prompt" and not self.prompt_id:
            raise ValueError("prompt_id is required when target_type is 'prompt'")
        if self.target_type == "chat" and not self.chat_id:
            raise ValueError("chat_id is required when target_type is 'chat'")
        if self.target_type == "message" and not (self.chat_id and self.message_id):
            raise ValueError("chat_id and message_id are both required when target_type is 'message'")
        return self


class ReviewOut(BaseModel):
    """
    What the server sends back. snapshot holds different shapes per
    target_type:
      - prompt  -> the prompt's text content (str)
      - chat    -> the full chat dict (messages + tokens, copied verbatim)
      - message -> the message's text content (str)
    """
    id: UUID
    target_type: Literal["prompt", "chat", "message"]
    prompt_id: Optional[UUID] = None
    chat_id: Optional[UUID] = None
    message_id: Optional[UUID] = None
    snapshot: Any
    reviewer_name: str
    score: int
    feedback: str
    reviewed_at: datetime


class ReviewSummary(BaseModel):
    """Shared response shape for /reviews/{prompt_id}/summary,
    /reviews/chat/{chat_id}/summary, and /reviews/message/{message_id}/summary."""
    target_id: UUID
    average_score: Optional[float] = None
    review_count: int
    feedback: list[str]
