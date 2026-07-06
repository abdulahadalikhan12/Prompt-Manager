import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime, Integer, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship

from database import Base


class Prompt(Base):
    """
    SQLAlchemy ORM model -- this class IS the database table.
    SQLAlchemy reads this class definition and knows to create a table
    called "prompts" with these exact columns, types, and constraints.

    This replaces what would have been a raw `CREATE TABLE prompts (...)`
    SQL string in the SQLite version of this project.
    """
    __tablename__ = "prompts"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    description = Column(String, nullable=True)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    chats = relationship("Chat", back_populates="prompt", cascade="all, delete-orphan")


class Chat(Base):
    """
    Week 2 addition. A Chat is created when a prompt is "executed" --
    it represents one ongoing conversation with the model, seeded from
    a specific prompt's content. Unlike Week 1 (where a prompt was just
    stored text), a Chat is where that text actually gets run.

    Uses a REAL SQLAlchemy ForeignKey to prompts.id, unlike review-service's
    prompt_id (which is "a foreign reference, not a DB foreign key" per
    the Week 1 brief) -- the difference is ownership: Chat lives in the
    SAME database as Prompt, owned by the same service, so a real FK
    constraint is appropriate here. review-service's prompt_id points
    at a row in a DIFFERENT service's database entirely, where a real
    FK is not even possible.
    """
    __tablename__ = "chats"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    prompt_id = Column(UUID(as_uuid=True), ForeignKey("prompts.id"), nullable=False)
    title = Column(String, nullable=True)
    total_tokens = Column(Integer, default=0, nullable=False)
    summary = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))

    prompt = relationship("Prompt", back_populates="chats")
    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan",
                             order_by="Message.created_at")
    documents = relationship("ChatDocument", back_populates="chat", cascade="all, delete-orphan",
                              order_by="ChatDocument.attached_at")


class Message(Base):
    """
    One turn in a Chat -- either the user's message or the assistant's
    reply. Token usage is stored per message (0 for user messages, real
    values for assistant replies). system_tokens is OUR locally-estimated
    count of the system-prompt portion of the input, so the UI can show
    a System / Input / Output breakdown -- OpenRouter only returns the
    combined prompt_tokens, so this split is computed before the call.
    """
    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    role = Column(String, nullable=False)  # "user" or "assistant"
    content = Column(Text, nullable=False)
    system_tokens = Column(Integer, default=0, nullable=False)
    prompt_tokens = Column(Integer, default=0, nullable=False)
    completion_tokens = Column(Integer, default=0, nullable=False)
    total_tokens = Column(Integer, default=0, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chat = relationship("Chat", back_populates="messages")


class ChatDocument(Base):
    """
    A document attached to a chat. document_id is the id this document
    holds in document-service -- it is NOT a SQL FK (different service,
    different storage) but a foreign reference, same pattern as
    review-service's prompt_id.

    extracted_text is cached here at attach time so a follow-up turn
    doesn't have to re-fetch the body from document-service every time
    we assemble the system prompt. This trades a small amount of
    duplication for predictable latency and self-contained chats.
    """
    __tablename__ = "chat_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id = Column(UUID(as_uuid=True), ForeignKey("chats.id"), nullable=False)
    document_id = Column(UUID(as_uuid=True), nullable=False)
    filename = Column(String, nullable=False)
    extracted_text = Column(Text, nullable=False)
    attached_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

    chat = relationship("Chat", back_populates="documents")
