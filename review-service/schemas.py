from typing import Optional
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class ReviewCreate(BaseModel):
    """What the client sends on POST /reviews."""
    prompt_id: UUID
    reviewer_name: str
    # Field(ge=1, le=5) means "greater-or-equal to 1, less-or-equal to 5".
    # Pydantic rejects anything outside that range automatically -- this
    # is the spec's "score must be validated as integer between 1 and 5"
    # requirement, satisfied with zero manual if-checks.
    score: int = Field(ge=1, le=5)
    feedback: str


class ReviewOut(BaseModel):
    """What the server sends back -- includes server-assigned fields
    and the prompt_snapshot copied at review time."""
    id: UUID
    prompt_id: UUID
    prompt_snapshot: str
    reviewer_name: str
    score: int
    feedback: str
    reviewed_at: datetime


class ReviewSummary(BaseModel):
    """Response shape for GET /reviews/{prompt_id}/summary."""
    prompt_id: UUID
    average_score: Optional[float] = None
    review_count: int
    feedback: list[str]
