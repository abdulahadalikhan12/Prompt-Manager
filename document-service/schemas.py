from datetime import datetime
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel


DocumentKind = Literal["pdf", "docx"]


class DocumentOut(BaseModel):
    """Metadata returned after upload and on GET /documents.
    `text` is omitted from list views (LIST endpoint sets it to None) so
    sending a large index doesn't drag every extracted body across the
    wire; fetch the body explicitly via /documents/{id}/text when needed."""
    id: UUID
    filename: str
    kind: DocumentKind
    size_bytes: int
    char_count: int
    uploaded_at: datetime
    text: Optional[str] = None


class DocumentText(BaseModel):
    """Just the extracted text body -- used by GET /documents/{id}/text
    so callers can fetch the heavy field on demand."""
    id: UUID
    text: str
