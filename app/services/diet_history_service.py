"""
app/services/diet_history_service.py

Persists generated diet plans tied to a user (or one of their family
members), and retrieves past diet plans for the history page.
"""

from sqlalchemy.orm import Session

from app.models import DietPlanRecord


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
        context=context,
        plan_text=plan_text,
        plan_html=plan_html,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_user_diet_plans(db: Session, user_id: int):
    return (
        db.query(DietPlanRecord)
        .filter(DietPlanRecord.user_id == user_id)
        .order_by(DietPlanRecord.created_at.desc())
        .all()
    )


def get_diet_plan_for_user(db: Session, record_id: int, user_id: int):
    return (
        db.query(DietPlanRecord)
        .filter(DietPlanRecord.id == record_id, DietPlanRecord.user_id == user_id)
        .first()
    )