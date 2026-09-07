"""
app/scripts/make_super_admin.py

یک کاربر را (بر اساس ایمیل یا شماره موبایل) به ادمین مستر (رئیس
بقیه‌ی ادمین‌ها) تبدیل می‌کند. اگر کاربر قبلاً platform_admin نباشد،
اول به این نقش ارتقا داده می‌شود.

اجرا با:
    python -m app.scripts.make_super_admin your@email.com
    python -m app.scripts.make_super_admin 09121234567
"""

import sys

from app.database import SessionLocal, init_db
from app.models import User, ROLE_PLATFORM_ADMIN
from app.core.logging_config import setup_logging, get_logger

setup_logging()
logger = get_logger(__name__)


def make_super_admin(identifier: str):
    identifier = identifier.strip()

    init_db()
    db = SessionLocal()

    try:
        user = (
            db.query(User).filter(User.email == identifier.lower()).first()
            or db.query(User).filter(User.phone == identifier).first()
        )

        if not user:
            logger.error(f"❌ کاربری با '{identifier}' پیدا نشد.")
            return

        user.role = ROLE_PLATFORM_ADMIN
        user.is_active = True
        user.verification_status = None
        user.is_super_admin = True

        db.commit()

        logger.info(f"✅ کاربر '{user.display_name}' اکنون ادمین مستر (رئیس بقیه‌ی ادمین‌ها) است.")

    finally:
        db.close()


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("استفاده صحیح: python -m app.scripts.make_super_admin your@email.com")
        sys.exit(1)

    make_super_admin(sys.argv[1])