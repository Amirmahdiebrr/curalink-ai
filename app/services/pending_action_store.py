"""
app/services/pending_action_store.py

Persistent (DB-backed) store برای داده‌ی لازم جهت اجرای واقعی یک
اکشن pay-per-use (تحلیل آزمایش/برنامه غذایی/آماده‌سازی ویزیت) بعد از
برگشت کاربر از درگاه زرین‌پال. کلید = Payment.id

نکته: بایت خام فایل دیگر مستقیماً اینجا نگه داشته نمی‌شود؛ کد
صداکننده (analyze.py) باید بایت فایل را قبل از ذخیره‌سازی به base64
تبدیل کند تا در ستون متنی دیتابیس قابل ذخیره باشد.

نکته‌ی امنیتی: این داده (که می‌تواند شامل بایت خام فایل پزشکی،
علائم بیمار و پروفایل سلامت باشد) قبل از ذخیره در دیتابیس با همان
کلید Fernet که برای فیلدهای حساس دیگر (مثل ocr_text و national_id)
استفاده می‌شود رمزنگاری می‌شود، تا در صورت دسترسی مستقیم به دیتابیس،
این اطلاعات موقت هم متن باز در دسترس نباشند.
"""

import json
from datetime import datetime, timedelta

from app.database import SessionLocal
from app.models import PendingActionRecord
from app.core.crypto import encrypt_value, decrypt_value
from app.core.logging_config import get_logger

logger = get_logger(__name__)

ACTION_MAX_AGE_SECONDS = 60 * 60 * 2  # ۲ ساعت


def save(payment_id: int, data: dict):
    db = SessionLocal()
    try:
        existing = db.query(PendingActionRecord).filter(PendingActionRecord.payment_id == payment_id).first()
        data_json = json.dumps(data, ensure_ascii=False)
        encrypted_data_json = encrypt_value(data_json)

        if existing:
            existing.data_json = encrypted_data_json
            existing.result_type = None
            existing.result_id = None
            existing.error = None
        else:
            db.add(PendingActionRecord(
                payment_id=payment_id,
                data_json=encrypted_data_json,
                result_type=None,
                result_id=None,
                error=None,
            ))

        db.commit()
    finally:
        db.close()


def get(payment_id: int) -> dict | None:
    db = SessionLocal()
    try:
        record = db.query(PendingActionRecord).filter(PendingActionRecord.payment_id == payment_id).first()

        if record is None:
            return None

        decrypted_data_json = decrypt_value(record.data_json)

        return {
            "data": json.loads(decrypted_data_json),
            "result_type": record.result_type,
            "result_id": record.result_id,
            "error": record.error,
        }
    finally:
        db.close()


def update(payment_id: int, **kwargs):
    db = SessionLocal()
    try:
        record = db.query(PendingActionRecord).filter(PendingActionRecord.payment_id == payment_id).first()

        if record is None:
            return

        for key, value in kwargs.items():
            setattr(record, key, value)

        db.commit()
    finally:
        db.close()


def delete(payment_id: int):
    db = SessionLocal()
    try:
        record = db.query(PendingActionRecord).filter(PendingActionRecord.payment_id == payment_id).first()

        if record:
            db.delete(record)
            db.commit()
    finally:
        db.close()


def purge_old():
    cutoff = datetime.utcnow() - timedelta(seconds=ACTION_MAX_AGE_SECONDS)

    db = SessionLocal()
    count = 0
    try:
        expired = db.query(PendingActionRecord).filter(PendingActionRecord.created_at < cutoff).all()
        count = len(expired)

        for record in expired:
            db.delete(record)

        db.commit()
    finally:
        db.close()

    if count:
        logger.info(f"[PendingActionStore] Purged {count} expired action(s)")