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
