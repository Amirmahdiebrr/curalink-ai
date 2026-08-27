"""add price mismatch tracking columns to analysis_records

Revision ID: 0004
Revises: 0003
Create Date: 2025-01-04 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.add_column(sa.Column("requested_exam_type", sa.String(), nullable=True))
        batch_op.add_column(sa.Column("price_paid", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("price_mismatch_flag", sa.Boolean(), nullable=False, server_default=sa.false()))
        batch_op.add_column(sa.Column("price_mismatch_amount", sa.Integer(), nullable=True))
        batch_op.create_index(
            "ix_analysis_records_price_mismatch_flag", ["price_mismatch_flag"], unique=False
        )


def downgrade() -> None:
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.drop_index("ix_analysis_records_price_mismatch_flag")
        batch_op.drop_column("price_mismatch_amount")
        batch_op.drop_column("price_mismatch_flag")
        batch_op.drop_column("price_paid")
        batch_op.drop_column("requested_exam_type")