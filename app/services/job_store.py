"""
app/services/job_store.py

Persistent (DB-backed) job tracking برای job های تحلیل آزمایش در
پس‌زمینه (status، stage، result، error)، کلید = job_id.

قبلاً این یک دیکشنری در-حافظه‌ی پروسه بود؛ با چند worker یا ری‌استارت
سرور، وقتی کاربر /status/{job_id} را poll می‌کرد به یک worker دیگر
می‌رسید که اصلاً این job را نداشت و 404 می‌گرفت. حالا در جدول jobs
دیتابیس ذخیره می‌شود که بین همه‌ی worker ها مشترک است.
"""

import json
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import JobRecord

JOB_MAX_AGE_SECONDS = 60 * 60 * 2  # ۲ ساعت


def create_job(exam_type: str | None, user_id: int | None = None) -> str:
    import uuid
    job_id = uuid.uuid4().hex

    db = SessionLocal()
    try:
        record = JobRecord(
            job_id=job_id,
            exam_type=exam_type,
            user_id=user_id,
            status="pending",
            stage="pending",
            result_json=None,
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
        record = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()

        if record is None:
            return

        if "result" in kwargs:
            result_value = kwargs.pop("result")
            record.result_json = (
                json.dumps(result_value, ensure_ascii=False) if result_value is not None else None
            )

        for key, value in kwargs.items():
            setattr(record, key, value)

        record.updated_at = datetime.utcnow()

        db.commit()
    finally:
        db.close()


def get_job(job_id: str) -> dict | None:
    db = SessionLocal()
    try:
        record = db.query(JobRecord).filter(JobRecord.job_id == job_id).first()

        if record is None:
            return None

        return {
            "job_id": record.job_id,
            "exam_type": record.exam_type,
            "user_id": record.user_id,
            "status": record.status,
            "stage": record.stage,
            "result": json.loads(record.result_json) if record.result_json else None,
            "error": record.error,
        }
    finally:
        db.close()


def purge_old_jobs():
    cutoff = datetime.utcnow() - timedelta(seconds=JOB_MAX_AGE_SECONDS)

    db = SessionLocal()
    count = 0
    try:
        expired = db.query(JobRecord).filter(JobRecord.created_at < cutoff).all()
        count = len(expired)

        for record in expired:
            db.delete(record)

        db.commit()
    finally:
        db.close()

    if count:
        print(f"[JobStore] Purged {count} expired job(s)", flush=True)