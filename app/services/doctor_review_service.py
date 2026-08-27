"""
app/services/doctor_review_service.py

جریان بررسی گزارش توسط پزشک: بیمار درخواست بررسی می‌دهد (رایگان اگر
اشتراک/دسترسی نامحدود دارد، وگرنه از طریق پرداخت pay-per-use)، پزشک
از صف گزارش‌های در انتظار یکی را انتخاب و نظر خود را ثبت می‌کند.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    AnalysisRecord, DoctorPayout,
    DOCTOR_REVIEW_AWAITING_DOCTOR, DOCTOR_REVIEW_REVIEWED,
    DOCTOR_PAYOUT_PENDING,
)
from app.core.crypto import decrypt_value, encrypt_value
from app.services.billing_service import get_doctor_review_pricing
from app.core.logging_config import get_logger

logger = get_logger(__name__)


class DoctorReviewError(Exception):
    pass


def _decrypt_for_view(record: AnalysisRecord) -> AnalysisRecord:
    if record is None:
        return record
    record.ocr_text = decrypt_value(record.ocr_text)
    record.analysis_text = decrypt_value(record.analysis_text)
    record.analysis_html = decrypt_value(record.analysis_html)
    record.symptoms = decrypt_value(record.symptoms)
    record.doctor_opinion_text = decrypt_value(record.doctor_opinion_text)
    return record


def _get_record_for_patient(db: Session, record_id: int, user_id: int) -> AnalysisRecord:
    record = (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.id == record_id, AnalysisRecord.user_id == user_id)
        .first()
    )

    if not record:
        raise DoctorReviewError("این گزارش پیدا نشد یا به شما تعلق ندارد.")

    if record.review_status == DOCTOR_REVIEW_AWAITING_DOCTOR:
        raise DoctorReviewError("این گزارش قبلاً برای بررسی ارسال شده و در انتظار پزشک است.")

    if record.review_status == DOCTOR_REVIEW_REVIEWED:
        raise DoctorReviewError("این گزارش قبلاً توسط پزشک بررسی شده است.")

    return record


def can_request_review(db: Session, record_id: int, user_id: int) -> bool:
    """
    فقط اعتبارسنجی می‌کند که آیا این گزارش الان قابل ارسال برای بررسی
    است، بدون تغییر وضعیت — برای بررسی قبل از هدایت به درگاه پرداخت.
    """
    try:
        _get_record_for_patient(db, record_id, user_id)
        return True
    except DoctorReviewError:
        return False


def mark_review_requested(db: Session, record_id: int, user_id: int, price_paid: int | None) -> AnalysisRecord:
    """
    وضعیت گزارش را به «در انتظار پزشک» تغییر می‌دهد. این تابع یا بعد
    از تایید رایگان بودن (اشتراک/دسترسی نامحدود) صدا زده می‌شود، یا
    بعد از پرداخت موفق pay-per-use (از callback درگاه پرداخت).
    """
    record = _get_record_for_patient(db, record_id, user_id)

    record.review_status = DOCTOR_REVIEW_AWAITING_DOCTOR
    record.review_payment_status = "paid" if price_paid else "free_via_subscription"
    record.review_price_paid = price_paid

    db.commit()
    db.refresh(record)

    return record


def get_awaiting_reviews(db: Session):
    """
    صف گزارش‌های در انتظار بررسی (برای داشبورد پزشک).
    """
    return (
        db.query(AnalysisRecord)
        .filter(AnalysisRecord.review_status == DOCTOR_REVIEW_AWAITING_DOCTOR)
        .order_by(AnalysisRecord.created_at.asc())
        .all()
    )


def get_my_reviewed_records(db: Session, doctor_id: int):
    return (
        db.query(AnalysisRecord)
        .filter(
            AnalysisRecord.reviewing_doctor_id == doctor_id,
            AnalysisRecord.review_status == DOCTOR_REVIEW_REVIEWED,
        )
        .order_by(AnalysisRecord.doctor_opinion_at.desc())
        .all()
    )


def get_record_for_doctor(db: Session, record_id: int) -> AnalysisRecord | None:
    """
    دسترسی پزشک به یک گزارش خاص — بدون محدودیت به مالکیت رکورد، اما
    فقط اگر در انتظار بررسی باشد یا قبلاً بررسی شده باشد (نه هر گزارشی).
    """
    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()

    if not record:
        return None

    if record.review_status not in (DOCTOR_REVIEW_AWAITING_DOCTOR, DOCTOR_REVIEW_REVIEWED):
        return None

    return _decrypt_for_view(record)


def submit_review(db: Session, record_id: int, doctor_id: int, opinion_text: str) -> AnalysisRecord:

    record = db.query(AnalysisRecord).filter(AnalysisRecord.id == record_id).first()

    if not record:
        raise DoctorReviewError("گزارش پیدا نشد.")

    if record.review_status != DOCTOR_REVIEW_AWAITING_DOCTOR:
        raise DoctorReviewError("این گزارش در وضعیت قابل‌بررسی نیست (شاید توسط پزشک دیگری بررسی شده).")

    opinion_text = (opinion_text or "").strip()

    if not opinion_text:
        raise DoctorReviewError("متن نظر پزشک نمی‌تواند خالی باشد.")

    record.reviewing_doctor_id = doctor_id
    record.doctor_opinion_text = encrypt_value(opinion_text)
    record.doctor_opinion_status = "submitted"
    record.doctor_opinion_at = datetime.utcnow()
    record.review_status = DOCTOR_REVIEW_REVIEWED

    db.commit()

    # ثبت سهم پزشک برای تسویه‌ی آینده (فقط رکورد pending؛ مکانیزم
    # پرداخت واقعی به پزشکان هنوز پیاده نشده)
    try:
        pricing = get_doctor_review_pricing(db)
        db.add(DoctorPayout(
            doctor_id=doctor_id,
            analysis_id=record.id,
            amount=pricing["doctor_share"],
            status=DOCTOR_PAYOUT_PENDING,
        ))
        db.commit()
    except Exception as e:
        logger.error(f"[DoctorReview] Failed to create payout record: {e}")

    db.refresh(record)

    return _decrypt_for_view(record)