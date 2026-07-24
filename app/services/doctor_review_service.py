"""
app/services/doctor_review_service.py

جریان بررسی گزارش توسط پزشک: بیمار درخواست بررسی می‌دهد، پزشک از صف
گزارش‌های در انتظار یکی را انتخاب و نظر خود را ثبت می‌کند.

نکته مهم: در این نسخه (پروتوتایپ اولیه)، پرداخت واقعی برای این سرویس
هنوز وصل نشده (چون درگاه پرداخت فعال نیست). درخواست بررسی فعلاً
رایگان ثبت می‌شود. قبل از رفتن به production باید این جریان مثل
diet_service/visit_prep_service به start_service_payment وصل شود
(چک اشتراک رایگان بیمار + در غیر این صورت پرداخت pay-per-use).
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


def request_review(db: Session, record_id: int, user_id: int) -> AnalysisRecord:
    """
    بیمار درخواست بررسی توسط پزشک را برای یکی از گزارش‌های خودش ثبت می‌کند.
    """
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

    record.review_status = DOCTOR_REVIEW_AWAITING_DOCTOR
    # TODO: قبل از production، اینجا باید بررسی اشتراک/پرداخت وصل شود.
    record.review_payment_status = "pending_gateway_setup"

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