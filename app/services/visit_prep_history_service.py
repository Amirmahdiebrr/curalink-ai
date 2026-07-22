"""
app/services/visit_prep_history_service.py

Persists generated doctor-visit prep summaries tied to a user (or one
of their family members), and retrieves past summaries for the
history page.
"""

from sqlalchemy.orm import Session

from app.models import VisitPrepRecord


def save_visit_prep(
    db: Session,
    user_id: int,
    family_member_id: int | None,
    visit_reason: str | None,
    summary_text: str,
    summary_html: str,
) -> VisitPrepRecord:

    record = VisitPrepRecord(
        user_id=user_id,
        family_member_id=family_member_id,
        visit_reason=visit_reason,
        summary_text=summary_text,
        summary_html=summary_html,
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    return record


def get_user_visit_preps(db: Session, user_id: int):
    return (
        db.query(VisitPrepRecord)
        .filter(VisitPrepRecord.user_id == user_id)
        .order_by(VisitPrepRecord.created_at.desc())
        .all()
    )


def get_visit_prep_for_user(db: Session, record_id: int, user_id: int):
    return (
        db.query(VisitPrepRecord)
        .filter(VisitPrepRecord.id == record_id, VisitPrepRecord.user_id == user_id)
        .first()
    )