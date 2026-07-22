"""
app/services/diet_history_service.py

Persists generated diet plans tied to a user (or one of their
family members), and retrieves past plans for the history page.

Free-text fields (context, plan_text, plan_html) are encrypted at
rest since they can reflect personal health details.
"""

from sqlalchemy.orm import Session

from app.models import DietPlanRecord
from app.core.crypto import encrypt_value, decrypt_value


def _decrypt_record(record: DietPlanRecord) -> DietPlanRecord:
    if record is None:
        return record
    record.context = decrypt_value(record.context)
    record.plan_text = decrypt_value(record.plan_text)
    record.plan_html = decrypt_value(record.plan_html)
    return record


def save_diet_plan(
    db: Session,
    user_id: int,
    family_member_id: int | None,
    context: str | None,
    plan_text: str,
    plan_html: str,
) -> DietPlanRecord:

    record = DietPlanRecord(
        user_id=user_id,
        family_member_id=family_member_id,
        context=encrypt_value(context),
        plan_text=encrypt_value(plan_text),
        plan_html=encrypt_value(plan_html),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_user_diet_plans(db: Session, user_id: int):
    records = (
        db.query(DietPlanRecord)
        .filter(DietPlanRecord.user_id == user_id)
        .order_by(DietPlanRecord.created_at.desc())
        .all()
    )
    return [_decrypt_record(r) for r in records]


def get_diet_plan_for_user(db: Session, record_id: int, user_id: int):
    record = (
        db.query(DietPlanRecord)
        .filter(DietPlanRecord.id == record_id, DietPlanRecord.user_id == user_id)
        .first()
    )
    return _decrypt_record(record)