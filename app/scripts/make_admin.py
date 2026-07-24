"""
app/scripts/make_admin.py

یک کاربر ثبت‌نام‌شده را به نقش platform_admin ارتقا می‌دهد. این اکانت
پس از ارتقا:
- به /admin (داشبورد نظارتی) و /admin/doctors دسترسی دارد
- در آنالیز آزمایش، برنامه غذایی و آماده‌سازی ویزیت به‌صورت رایگان و
  نامحدود دسترسی دارد (بدون نیاز به اشتراک یا پرداخت — bypass در
  billing_service.py)
- به صف بررسی گزارش‌ها توسط پزشک (/doctor/reviews) هم دسترسی دارد

نکته: این کاربر باید از قبل با ایمیل/رمز عبور ثبت‌نام کرده باشد
(از /register/patient). این اسکریپت فقط نقش را عوض می‌کند.

اجرا با:
    python -m app.scripts.make_admin your@email.com
"""

import sys

from app.database import SessionLocal, init_db
from app.models import User, ROLE_PLATFORM_ADMIN
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def make_admin(email: str):
    email = email.strip().lower()

    init_db()
    db = SessionLocal()

    try:
        user = db.query(User).filter(User.email == email).first()

        if not user:
            logger.error(f"❌ کاربری با ایمیل '{email}' پیدا نشد.")
            logger.error("اول باید از صفحه‌ی /register/patient با همین ایمیل ثبت‌نام کرده باشی.")
            return

        user.role = ROLE_PLATFORM_ADMIN
        user.is_active = True
        user.verification_status = None

        db.commit()

        logger.info(f"✅ کاربر '{email}' با موفقیت به ادمین پلتفرم (platform_admin) ارتقا یافت.")
        logger.info("این اکانت الان به /admin دسترسی داره و در همه‌ی سرویس‌های پولی رایگان و نامحدوده.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("استفاده صحیح: python -m app.scripts.make_admin your@email.com")
        sys.exit(1)

    make_admin(sys.argv[1])