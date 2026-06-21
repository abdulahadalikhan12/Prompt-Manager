import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Text, DateTime
from sqlalchemy.dialects.postgresql import UUID

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
    tags = Column(String, nullable=True)  # comma-separated string, per spec
    model_target = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc),
                         onupdate=lambda: datetime.now(timezone.utc))
