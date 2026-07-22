from dotenv import load_dotenv
import os
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "nvidia"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "deepseek-ai/deepseek-v4-pro"
)

NVIDIA_API_KEY = os.getenv(
    "NVIDIA_API_KEY"
)

if NVIDIA_API_KEY:
    print("✅ NVIDIA API KEY loaded")
else:
    print("❌ NVIDIA API KEY missing")

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

if not SESSION_SECRET_KEY:
    SESSION_SECRET_KEY = secrets.token_hex(32)
    print("⚠️  SESSION_SECRET_KEY not set in .env — using a temporary random key (sessions will reset on restart).")

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    ENCRYPTION_KEY = Fernet.generate_key().decode("utf-8")
    print(
        "⚠️  ENCRYPTION_KEY not set in .env — using a temporary random key. "
        "Previously-encrypted fields (like national_id) will become UNREADABLE after restart. "
        "Set a persistent ENCRYPTION_KEY in .env for production."
    )
else:
    ENCRYPTION_KEY = ENCRYPTION_KEY.encode("utf-8")

# ==========================
# SMS Settings (9.1)
# ==========================

# "console" = no real panel yet, just logs the message.
# Set to a real provider key (e.g. "kavenegar") once a panel is purchased
# and implemented in app/services/sms_service.py.
SMS_PROVIDER = os.getenv("SMS_PROVIDER", "console")
# ==========================
# Email Settings
# ==========================

EMAIL_PROVIDER = os.getenv("EMAIL_PROVIDER", "console")

# آدرس پایه‌ی سایت، برای ساخت لینک‌های تایید ایمیل / بازیابی رمز
APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

# ==========================
# Doctor license uploads
# ==========================

DOCTOR_DOCS_MAX_SIZE_MB = 10
DOCTOR_DOCS_ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]