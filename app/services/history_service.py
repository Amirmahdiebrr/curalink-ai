"""
app/services/history_service.py

Persists analysis results tied to a logged-in user (or a family member
of that user), and retrieves past analyses and structured test values
for the history/trends/home pages.

Sensitive free-text fields (ocr_text, analysis_text, analysis_html,
symptoms, doctor_opinion_text) are encrypted at rest using the same
Fernet key used for national_id, since they can contain detailed
personal medical data.
"""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import AnalysisRecord, TestResult
from app.core.crypto import encrypt_value, decrypt_value


def _decrypt_record(record: AnalysisRecord) -> AnalysisRecord:
    if record is None:
        return record
    record.ocr_text = decrypt_value(record.ocr_text)
    record.analysis_text = decrypt_value(record.analysis_text)
    record.analysis_html = decrypt_value(record.analysis_html)
    record.symptoms = decrypt_value(record.symptoms)
    record.doctor_opinion_text = decrypt_value(record.doctor_opinion_text)
    return record


def save_analysis(
    db: Session,
    user_id: int,
    exam_type: str,
    filename: str,
    ocr_text: str,
    analysis_text: str,
    analysis_html: str,
    structured_results: list | None = None,
    symptoms: str | None = None,
    family_member_id: int | None = None,
) -> AnalysisRecord:

    record = AnalysisRecord(
        user_id=user_id,
        family_member_id=family_member_id,
        exam_type=exam_type,
        filename=filename,
        ocr_text=encrypt_value(ocr_text),
        analysis_text=encrypt_value(analysis_text),
        analysis_html=encrypt_value(analysis_html),
        symptoms=encrypt_value(symptoms),
    )

    db.add(record)
    db.commit()
    db.refresh(record)

    if structured_results:
        for item in structured_results:
            try:
                name = str(item.get("name", "")).strip()
                if not name:
                    continue

                value_numeric = item.get("value")
                try:
                    value_numeric = float(value_numeric)
                except (TypeError, ValueError):
                    value_numeric = None

                followup_days = item.get("recommended_followup_days")
                try:
                    followup_days = int(followup_days) if followup_days is not None else None
                except (TypeError, ValueError):
                    followup_days = None

                organ_category = item.get("organ_category")

                test_result = TestResult(
                    user_id=user_id,
                    analysis_id=record.id,
                    family_member_id=family_member_id,
                    test_name=name,
                    value_numeric=value_numeric,
                    value_text=str(item.get("value", "")),
                    unit=item.get("unit"),
                    reference_range=item.get("reference_range"),
                    status=item.get("status"),
                    recommended_followup_days=followup_days,
                    organ_category=organ_category,
                    test_date=record.created_at,
                )
                db.add(test_result)

            except Exception as e:
                print(f"[History] Skipped invalid structured item: {e}", flush=True)

        db.commit()

    return record


def get_user_history(db: Session, user_id: int):
    return (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.user_id == user_id)
        .order_by(AnalysisRecord.created_at.desc())
        .all()
    )


def get_record_for_user(db: Session, record_id: int, user_id: int):
    record = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == record_id, AnalysisRecord.user_id == user_id)
        .first()
    )
    return _decrypt_record(record)


def get_record_for_admin(db: Session, record_id: int):
    """
    مثل get_record_for_user، اما بدون محدودیت به مالک رکورد — فقط
    برای پنل نظارتی platform_admin استفاده می‌شود.
    """
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()
    return _decrypt_record(record)


def get_test_results_for_analysis(db: Session, analysis_id: int):
    """
    Returns all TestResult rows tied to a specific analysis record,
    used to rebuild the organ-grouped view for a saved history record.
    """
    return (
        db.query(TestResult)
        .filter(TestResult.analysis_id == analysis_id)
        .order_by(TestResult.test_name)
        .all()
    )


def get_latest_results_by_test(db: Session, user_id: int, family_member_id: int | None = None):
    """
    Returns the most recent TestResult row for each distinct test_name
    belonging to this user (or a specific family member), ordered by
    test_date descending.
    """

    query = db.query(TestResult).filter(
        TestResult.user_id == user_id,
        TestResult.value_numeric.isnot(None),
        TestResult.family_member_id == family_member_id,
    )

    all_results = query.order_by(TestResult.test_date.desc()).all()

    latest_by_name = {}

    for result in all_results:
        if result.test_name not in latest_by_name:
            latest_by_name[result.test_name] = result

    return list(latest_by_name.values())


def get_test_history(db: Session, user_id: int, test_name: str, family_member_id: int | None = None):
    return (
        db.query(TestResult)
        .filter(
            TestResult.user_id == user_id,
            TestResult.test_name == test_name,
            TestResult.value_numeric.isnot(None),
            TestResult.family_member_id == family_member_id,
        )
        .order_by(TestResult.test_date.asc())
        .all()
    )


def get_distinct_test_names(db: Session, user_id: int, family_member_id: int | None = None):
    rows = (
        db.query(TestResult.test_name)
        .filter(
            TestResult.user_id == user_id,
            TestResult.value_numeric.isnot(None),
            TestResult.family_member_id == family_member_id,
        )
        .distinct()
        .order_by(TestResult.test_name)
        .all()
    )
    return [row[0] for row in rows]


def get_due_followups(db: Session, user_id: int):
    """
    Returns test results (across the user and all their family members)
    whose recommended follow-up date has already arrived. Only the most
    recent result per (person, test_name) is considered, so an already
    re-tested item won't keep showing up as due.
    """

    rows = (
        db.query(TestResult)
        .filter(
            TestResult.user_id == user_id,
            TestResult.recommended_followup_days.isnot(None),
        )
        .order_by(TestResult.test_date.desc())
        .all()
    )

    latest_by_key = {}

    for row in rows:
        key = (row.family_member_id, row.test_name)
        if key not in latest_by_key:
            latest_by_key[key] = row

    now = datetime.utcnow()
    due_items = []

    for row in latest_by_key.values():
        due_date = row.test_date + timedelta(days=row.recommended_followup_days)
        if due_date <= now:
            due_items.append({
                "test_name": row.test_name,
                "due_date": due_date,
                "person_name": row.family_member.name if row.family_member else None,
            })

    due_items.sort(key=lambda item: item["due_date"])

    return due_items


def get_due_reminders_for_all_users(db: Session):
    """
    Returns TestResult rows (across ALL users) whose recommended
    follow-up date has arrived and for which a reminder has not been
    sent yet. Used by the daily reminder scheduler (9.2). Only the
    most recent result per (user, person, test_name) is considered.
    """

    rows = (
        db.query(TestResult)
        .filter(
            TestResult.recommended_followup_days.isnot(None),
            TestResult.followup_reminder_sent.is_(False),
        )
        .order_by(TestResult.test_date.desc())
        .all()
    )

    latest_by_key = {}

    for row in rows:
        key = (row.user_id, row.family_member_id, row.test_name)
        if key not in latest_by_key:
            latest_by_key[key] = row

    now = datetime.utcnow()
    due_rows = []

    for row in latest_by_key.values():
        due_date = row.test_date + timedelta(days=row.recommended_followup_days)
        if due_date <= now:
            due_rows.append(row)

    return due_rows