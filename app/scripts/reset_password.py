import sys
from app.database import SessionLocal, init_db
from app.models import User
from app.core.security import hash_password

def run(identifier: str, new_password: str):
    init_db()
    db = SessionLocal()
    try:
        user = (
            db.query(User).filter(User.email == identifier).first()
            or db.query(User).filter(User.phone == identifier).first()
        )
        if not user:
            print("❌ کاربر پیدا نشد.")
            return
        user.password_hash = hash_password(new_password)
        db.commit()
        print(f"✅ رمز عبور کاربر '{user.display_name}' با موفقیت تغییر کرد.")
    finally:
        db.close()

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("استفاده: python -m app.scripts.reset_password <email_or_phone> <new_password>")
        sys.exit(1)
    run(sys.argv[1], sys.argv[2])