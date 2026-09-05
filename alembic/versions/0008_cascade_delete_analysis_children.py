"""add ondelete=CASCADE to test_results/doctor_notes/prescriptions/prescription_items,
and ondelete=SET NULL to patient_followups.analysis_id

Revision ID: 0008
Revises: 0007
Create Date: 2025-01-08 00:00:00

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0008"
down_revision: Union[str, None] = "0007"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("test_results") as batch_op:
        batch_op.drop_constraint("test_results_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "test_results_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("doctor_notes") as batch_op:
        batch_op.drop_constraint("doctor_notes_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "doctor_notes_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.drop_constraint("prescriptions_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "prescriptions_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("prescription_items") as batch_op:
        batch_op.drop_constraint("prescription_items_prescription_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "prescription_items_prescription_id_fkey", "prescriptions", ["prescription_id"], ["id"], ondelete="CASCADE"
        )

    with op.batch_alter_table("patient_followups") as batch_op:
        batch_op.drop_constraint("patient_followups_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "patient_followups_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"], ondelete="SET NULL"
        )


def downgrade() -> None:
    with op.batch_alter_table("patient_followups") as batch_op:
        batch_op.drop_constraint("patient_followups_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "patient_followups_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"]
        )

    with op.batch_alter_table("prescription_items") as batch_op:
        batch_op.drop_constraint("prescription_items_prescription_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "prescription_items_prescription_id_fkey", "prescriptions", ["prescription_id"], ["id"]
        )

    with op.batch_alter_table("prescriptions") as batch_op:
        batch_op.drop_constraint("prescriptions_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "prescriptions_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"]
        )

    with op.batch_alter_table("doctor_notes") as batch_op:
        batch_op.drop_constraint("doctor_notes_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "doctor_notes_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"]
        )

    with op.batch_alter_table("test_results") as batch_op:
        batch_op.drop_constraint("test_results_analysis_id_fkey", type_="foreignkey")
        batch_op.create_foreign_key(
            "test_results_analysis_id_fkey", "analysis_records", ["analysis_id"], ["id"]
        )