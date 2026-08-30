"""add ondelete=CASCADE to doctor_profiles/organization_profiles/family_members user_id

Revision ID: 0006
Revises: 0005
Create Date: 2025-01-06 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("doctor_profiles") as batch_op:
        batch_op.drop_constraint("doctor_profiles_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "doctor_profiles_user_id_fkey", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("organization_profiles") as batch_op:
        batch_op.drop_constraint("organization_profiles_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "organization_profiles_user_id_fkey", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("family_members") as batch_op:
        batch_op.drop_constraint("family_members_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "family_members_user_id_fkey", "users", ["user_id"], ["id"], ondelete="CASCADE"
        )


def downgrade() -> None:
    with op.batch_alter_table("family_members") as batch_op:
        batch_op.drop_constraint("family_members_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "family_members_user_id_fkey", "users", ["user_id"], ["id"]
        )

    with op.batch_alter_table("organization_profiles") as batch_op:
        batch_op.drop_constraint("organization_profiles_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "organization_profiles_user_id_fkey", "users", ["user_id"], ["id"]
        )

    with op.batch_alter_table("doctor_profiles") as batch_op:
        batch_op.drop_constraint("doctor_profiles_user_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "doctor_profiles_user_id_fkey", "users", ["user_id"], ["id"]
        )