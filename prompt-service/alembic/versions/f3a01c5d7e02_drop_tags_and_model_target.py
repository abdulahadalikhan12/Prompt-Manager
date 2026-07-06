"""drop tags and model_target from prompts

Revision ID: f3a01c5d7e02
Revises: bd1380a5879a
Create Date: 2026-06-30 11:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3a01c5d7e02"
down_revision: Union[str, Sequence[str], None] = "bd1380a5879a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column("prompts", "tags")
    op.drop_column("prompts", "model_target")


def downgrade() -> None:
    op.add_column("prompts", sa.Column("model_target", sa.String(), nullable=True))
    op.add_column("prompts", sa.Column("tags", sa.String(), nullable=True))
