"""
app/services/history_service.py

Persists analysis results tied to a logged-in user, and retrieves
past analyses and structured test values for the history/trends pages.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import AnalysisRecord, TestResult


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
) -> AnalysisRecord:

    record = AnalysisRecord(
        user_id=user_id,
        exam_type=exam_type,
        filename=filename,
        ocr_text=ocr_text,
        analysis_text=analysis_text,
        analysis_html=analysis_html,
        symptoms=symptoms,
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

                test_result = TestResult(
                    user_id=user_id,
                    analysis_id=record.id,
                    test_name=name,
                    value_numeric=value_numeric,
                    value_text=str(item.get("value", "")),
                    unit=item.get("unit"),
                    reference_range=item.get("reference_range"),
                    status=item.get("status"),
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
    return (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == record_id, AnalysisRecord.user_id == user_id)
        .first()
    )


def get_latest_results_by_test(db: Session, user_id: int):
    """
    Returns the most recent TestResult row for each distinct test_name
    belonging to this user, ordered by test_date descending.
    """

    all_results = (
        db.query(TestResult)
        .filter(TestResult.user_id == user_id, TestResult.value_numeric.isnot(None))
        .order_by(TestResult.test_date.desc())
        .all()
    )

    latest_by_name = {}

    for result in all_results:
        if result.test_name not in latest_by_name:
            latest_by_name[result.test_name] = result

    return list(latest_by_name.values())


def get_test_history(db: Session, user_id: int, test_name: str):
    return (
        db.query(TestResult)
        .filter(
            TestResult.user_id == user_id,
            TestResult.test_name == test_name,
            TestResult.value_numeric.isnot(None),
        )
        .order_by(TestResult.test_date.asc())
        .all()
    )


def get_distinct_test_names(db: Session, user_id: int):
    rows = (
        db.query(TestResult.test_name)
        .filter(TestResult.user_id == user_id, TestResult.value_numeric.isnot(None))
        .distinct()
        .order_by(TestResult.test_name)
        .all()
    )
    return [row[0] for row in rows]