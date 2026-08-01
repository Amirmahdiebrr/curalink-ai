"""
app/services/workout_history_service.py
"""

from sqlalchemy.orm import Session

from app.models import WorkoutPlanRecord
from app.core.crypto import encrypt_value, decrypt_value


def _decrypt_record(record: WorkoutPlanRecord) -> WorkoutPlanRecord:
    if record is None:
        return record
    record.injuries = decrypt_value(record.injuries)
    record.plan_text = decrypt_value(record.plan_text)
    record.plan_html = decrypt_value(record.plan_html)
    return record


def save_workout_plan(
    db: Session,
    user_id: int,
    family_member_id: int | None,
    goal: str | None,
    fitness_level: str | None,
    days_per_week: int | None,
    equipment: str | None,
    injuries: str | None,
    plan_text: str,
    plan_html: str,
) -> WorkoutPlanRecord:

    record = WorkoutPlanRecord(
        user_id=user_id,
        family_member_id=family_member_id,
        goal=goal,
        fitness_level=fitness_level,
        days_per_week=days_per_week,
        equipment=equipment,
        injuries=encrypt_value(injuries),
        plan_text=encrypt_value(plan_text),
        plan_html=encrypt_value(plan_html),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_user_workout_plans(db: Session, user_id: int):
    records = (
        db.query(WorkoutPlanRecord)
        .filter(WorkoutPlanRecord.user_id == user_id)
        .order_by(WorkoutPlanRecord.created_at.desc())
        .all()
    )
    return [_decrypt_record(r) for r in records]


def get_workout_plan_for_user(db: Session, record_id: int, user_id: int):
    record = (
        db.query(WorkoutPlanRecord)
        .filter(WorkoutPlanRecord.id == record_id, WorkoutPlanRecord.user_id == user_id)
        .first()
    )
    return _decrypt_record(record)


def get_latest_workout_plan_for_person(db: Session, user_id: int, family_member_id: int | None):
    """
    آخرین برنامه‌ی ورزشی ثبت‌شده برای همین فرد (خود کاربر یا همان عضو
    خانواده)، برای تزریق به عنوان کانتکست «تداوم روند» به پرامپت.
    """
    record = (
        db.query(WorkoutPlanRecord)
        .filter(
            WorkoutPlanRecord.user_id == user_id,
            WorkoutPlanRecord.family_member_id == family_member_id,
        )
        .order_by(WorkoutPlanRecord.created_at.desc())
        .first()
    )
    return _decrypt_record(record)