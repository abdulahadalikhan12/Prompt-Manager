"""add chat_documents table and system_tokens column to messages

Revision ID: a47b8c92e1d4
Revises: f3a01c5d7e02
Create Date: 2026-06-30 13:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a47b8c92e1d4"
down_revision: Union[str, Sequence[str], None] = "f3a01c5d7e02"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column("system_tokens", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_table(
        "chat_documents",
        sa.Column("id", sa.UUID(), primary_key=True, nullable=False),
        sa.Column("chat_id", sa.UUID(), sa.ForeignKey("chats.id"), nullable=False),
        sa.Column("document_id", sa.UUID(), nullable=False),
        sa.Column("filename", sa.String(), nullable=False),
        sa.Column("extracted_text", sa.Text(), nullable=False),
        sa.Column("attached_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("chat_documents")
    op.drop_column("messages", "system_tokens")
