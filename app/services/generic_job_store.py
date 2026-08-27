"""
app/services/generic_job_store.py

Persistent (DB-backed) job tracking برای job های پس‌زمینه‌ی diet،
workout و visit-prep — دقیقاً مشابه app/services/job_store.py که
برای تحلیل آزمایش استفاده می‌شود، اما جدا نگه داشته شده چون این سه
سرویس به AnalysisRecord ربطی ندارند و نتیجه‌شان رکورد دیگری
(DietPlanRecord/WorkoutPlanRecord/VisitPrepRecord) است.
"""

import json
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import GenericJobRecord
from app.core.logging_config import get_logger

logger = get_logger(__name__)

GENERIC_JOB_MAX_AGE_SECONDS = 60 * 60 * 2  # ۲ ساعت


def create_job(job_type: str, user_id: int | None = None) -> str:
    import uuid
    job_id = uuid.uuid4().hex

    db = SessionLocal()
    try:
        record = GenericJobRecord(
            job_id=job_id,
            job_type=job_type,
            user_id=user_id,
            status="pending",
            result_type=None,
            result_id=None,
            error=None,
        )
        db.add(record)
        db.commit()
    finally:
        db.close()

    return job_id


def update_job(job_id: str, **kwargs):
    db = SessionLocal()
    try:
        record = db.query(GenericJobRecord).filter(GenericJobRecord.job_id == job_id).first()

        if record is None:
            return

        for key, value in kwargs.items():
            setattr(record, key, value)

        record.updated_at = datetime.utcnow()

        db.commit()
    finally:
        db.close()


def get_job(job_id: str) -> dict | None:
    db = SessionLocal()
    try:
        record = db.query(GenericJobRecord).filter(GenericJobRecord.job_id == job_id).first()

        if record is None:
            return None

        return {
            "job_id": record.job_id,
            "job_type": record.job_type,
            "user_id": record.user_id,
            "status": record.status,
            "result_type": record.result_type,
            "result_id": record.result_id,
            "error": record.error,
        }
    finally:
        db.close()


def purge_old_jobs():
    cutoff = datetime.utcnow() - timedelta(seconds=GENERIC_JOB_MAX_AGE_SECONDS)

    db = SessionLocal()
    count = 0
    try:
        expired = db.query(GenericJobRecord).filter(GenericJobRecord.created_at < cutoff).all()
        count = len(expired)

        for record in expired:
            db.delete(record)

        db.commit()
    finally:
        db.close()

    if count:
        logger.info(f"[GenericJobStore] Purged {count} expired job(s)")