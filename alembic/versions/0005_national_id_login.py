"""make email nullable, add national_id_hash for national-id login

Revision ID: 0005
Revises: 0004
Create Date: 2025-01-05 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.alter_column("email", existing_type=sa.String(), nullable=True)
        batch_op.add_column(sa.Column("national_id_hash", sa.String(), nullable=True))
        batch_op.create_index(
            "ix_users_national_id_hash", ["national_id_hash"], unique=True
        )


def downgrade() -> None:
    with op.batch_alter_table("users") as batch_op:
        batch_op.drop_index("ix_users_national_id_hash")
        batch_op.drop_column("national_id_hash")
        batch_op.alter_column("email", existing_type=sa.String(), nullable=False)