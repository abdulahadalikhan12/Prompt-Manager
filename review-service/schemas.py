from typing import Optional, Literal, Any
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field, model_validator


class ReviewCreate(BaseModel):
    """
    What the client sends on POST /reviews. Week 2 extends this beyond
    just prompt reviews: target_type tells review-service whether to
    fetch a prompt or a full chat from prompt-service, and exactly one
    of prompt_id / chat_id must be set, matching target_type.
    """
    target_type: Literal["prompt", "chat"] = "prompt"
    prompt_id: Optional[UUID] = None
    chat_id: Optional[UUID] = None
    reviewer_name: str
    score: int = Field(ge=1, le=5)
    feedback: str

    @model_validator(mode="after")
    def check_target_matches_id(self):
        """
        Enforces "exactly one of prompt_id/chat_id, matching target_type"
        as a single rule, rather than scattering if-checks across the
        router and service. A request with target_type="chat" but no
        chat_id (or with both ids set) is rejected here, automatically,
        before any of our own business logic runs -- same philosophy as
        Field(ge=1, le=5) on score.
        """
        if self.target_type == "prompt" and not self.prompt_id:
            raise ValueError("prompt_id is required when target_type is 'prompt'")
        if self.target_type == "chat" and not self.chat_id:
            raise ValueError("chat_id is required when target_type is 'chat'")
        return self


class ReviewOut(BaseModel):
    """
    What the server sends back. snapshot replaces Week 1's
    prompt_snapshot -- it now holds EITHER the prompt's text (for a
    prompt review) OR the full chat object as a dict (for a chat
    review), copied verbatim at review time either way.
    """
    id: UUID
    target_type: Literal["prompt", "chat"]
    prompt_id: Optional[UUID] = None
    chat_id: Optional[UUID] = None
    snapshot: Any
    reviewer_name: str
    score: int
    feedback: str
    reviewed_at: datetime


class ReviewSummary(BaseModel):
    """Response shape for GET /reviews/{prompt_id}/summary (Week 1,
    unchanged) and GET /reviews/chat/{chat_id}/summary (Week 2, new)."""
    target_id: UUID
    average_score: Optional[float] = None
    review_count: int
    feedback: list[str]
