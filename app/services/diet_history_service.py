"""
app/services/visit_prep_history_service.py

Persists generated doctor-visit prep summaries tied to a user (or one
of their family members), and retrieves past summaries for the
history page.

Free-text fields (visit_reason, summary_text, summary_html) are
encrypted at rest since they can reflect personal health details.
"""

from sqlalchemy.orm import Session

from app.models import VisitPrepRecord
from app.core.crypto import encrypt_value, decrypt_value


def _decrypt_record(record: VisitPrepRecord) -> VisitPrepRecord:
    if record is None:
        return record
    record.visit_reason = decrypt_value(record.visit_reason)
    record.summary_text = decrypt_value(record.summary_text)
    record.summary_html = decrypt_value(record.summary_html)
    return record


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
        visit_reason=encrypt_value(visit_reason),
        summary_text=encrypt_value(summary_text),
        summary_html=encrypt_value(summary_html),
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
    record = (
        db.query(VisitPrepRecord)
        .filter(VisitPrepRecord.id == record_id, VisitPrepRecord.user_id == user_id)
        .first()
    )
    return _decrypt_record(record)