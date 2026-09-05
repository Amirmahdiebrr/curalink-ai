"""
app/scripts/make_admin_by_phone.py

یک کاربر ثبت‌نام‌شده را بر اساس شماره موبایل به نقش platform_admin
ارتقا می‌دهد (برای کاربرانی که ایمیل ندارند).

اجرا با:
    python -m app.scripts.make_admin_by_phone 09121234567
"""

import sys

from app.database import SessionLocal, init_db
from app.models import User, ROLE_PLATFORM_ADMIN
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def make_admin(phone: str):
    phone = phone.strip()

    init_db()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.phone == phone).first()

        if not user:
            logger.error(f"❌ کاربری با شماره '{phone}' پیدا نشد.")
            return

        user.role = ROLE_PLATFORM_ADMIN
        user.is_active = True
        user.verification_status = None

        db.commit()

        logger.info(f"✅ کاربر '{user.display_name}' با موفقیت به ادمین پلتفرم ارتقا یافت.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("استفاده صحیح: python -m app.scripts.make_admin_by_phone 09121234567")
        sys.exit(1)

    make_admin(sys.argv[1])
