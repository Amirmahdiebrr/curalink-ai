"""add series_id to analysis_records for sequential/serial test tracking

Revision ID: 0007
Revises: 0006
Create Date: 2025-01-07 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0007"
down_revision: Union[str, None] = "0006"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.add_column(sa.Column("series_id", sa.String(), nullable=True))
        batch_op.create_index("ix_analysis_records_series_id", ["series_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.drop_index("ix_analysis_records_series_id")
        batch_op.drop_column("series_id")