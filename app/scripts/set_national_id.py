"""
app/scripts/set_national_id.py

برای کاربرانی که قبل از فعال شدن سیستم ورود با کد ملی ثبت‌نام کرده‌اند
(و بنابراین national_id_hash آن‌ها خالی است)، این اسکریپت یک کد ملی
برایشان ثبت می‌کند تا بتوانند با آن وارد شوند. جست‌وجوی کاربر بر
اساس ایمیل انجام می‌شود.

اجرا با:
    python -m app.scripts.set_national_id your@email.com 1234567890
"""

import sys

from app.database import SessionLocal, init_db
from app.models import User
from app.services.auth_service import set_national_id, AuthError
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def run(email: str, national_id: str):
    email = email.strip().lower()

    init_db()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.error(f"❌ کاربری با ایمیل '{email}' پیدا نشد.")
            return

        try:
            set_national_id(db, user, national_id)
        except AuthError as e:
            logger.error(f"❌ {e}")
            return

        logger.info(f"✅ کد ملی برای کاربر '{email}' با موفقیت ثبت شد.")
        logger.info("این کاربر الان می‌تواند با همین کد ملی و رمز عبور فعلی‌اش وارد شود.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("استفاده صحیح: python -m app.scripts.set_national_id your@email.com 1234567890")
        sys.exit(1)

    run(sys.argv[1], sys.argv[2])