"""add updated_at columns to users, analysis_records, payments, subscriptions, prescriptions

Revision ID: 0003
Revises: 0002
Create Date: 2025-01-03 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("payments") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))

    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.add_column(sa.Column("updated_at", sa.DateTime(), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("subscriptions") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("payments") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("analysis_records") as batch_op:
        batch_op.drop_column("updated_at")

    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_column("updated_at")