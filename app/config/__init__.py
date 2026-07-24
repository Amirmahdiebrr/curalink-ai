from dotenv import load_dotenv
import os
import sys
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

# مدل جایگزین (سریع‌تر/سبک‌تر) که در صورت timeout یا شلوغی (503) مدل
# اصلی، به‌صورت خودکار برای همان درخواست امتحان می‌شود تا کاربر با
# شکست کامل تحلیل مواجه نشود.
AI_FALLBACK_MODEL = os.getenv(
    "AI_FALLBACK_MODEL",
    "deepseek-ai/deepseek-v4-flash"
)

NVIDIA_API_KEY = os.getenv(
    "NVIDIA_API_KEY"
)

if NVIDIA_API_KEY:
    print("✅ NVIDIA API KEY loaded")
else:
    print("❌ NVIDIA API KEY missing")

# ==========================
# آدرس پایه سایت - باید قبل از چک production تعریف بشه
# ==========================

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

IS_PRODUCTION = APP_BASE_URL.startswith("https://")

# ==========================
# SESSION_SECRET_KEY و ENCRYPTION_KEY
#
# در production (یعنی APP_BASE_URL با https شروع بشه) این دو کلید
# باید حتماً در .env ست شده باشن. اگه ست نشده باشن و چند worker
# یا ری‌استارت داشته باشی:
#   - SESSION_SECRET_KEY رندوم -> همه‌ی کاربرها logout می‌شن /
#     بین worker های مختلف سشن معتبر نیست
#   - ENCRYPTION_KEY رندوم -> داده‌های رمزنگاری‌شده‌ی قبلی
#     (ocr_text, analysis_text, national_id و...) غیرقابل‌بازیابی
#     و به‌صورت متن نامفهوم به کاربر نمایش داده می‌شن
#
# بنابراین در production این دو رو اجباری می‌کنیم (fail-fast) تا
# اپ اصلاً بالا نیاد به‌جای اینکه بی‌سروصدا دیتا خراب کنه.
# در حالت development (localhost) همچنان کلید موقت تولید می‌شه
# تا کار توسعه راحت بمونه.
# ==========================

SESSION_SECRET_KEY = os.getenv("SESSION_SECRET_KEY")

if not SESSION_SECRET_KEY:
    if IS_PRODUCTION:
        print(
            "❌ FATAL: SESSION_SECRET_KEY در .env تنظیم نشده است. "
            "در محیط Production این مقدار اجباری است چون در نبود آن، "
            "با هر ری‌استارت یا هر worker جدید، سشن کاربران نامعتبر "
            "می‌شود. اپلیکیشن متوقف شد.",
            flush=True
        )
        sys.exit(1)
    else:
        SESSION_SECRET_KEY = secrets.token_hex(32)
        print(
            "⚠️  SESSION_SECRET_KEY تنظیم نشده — از یک کلید موقت تصادفی "
            "استفاده می‌شود (فقط برای محیط توسعه). سشن‌ها با ری‌استارت "
            "سرور از بین می‌روند.",
            flush=True
        )

ENCRYPTION_KEY = os.getenv("ENCRYPTION_KEY")

if not ENCRYPTION_KEY:
    if IS_PRODUCTION:
        print(
            "❌ FATAL: ENCRYPTION_KEY در .env تنظیم نشده است. "
            "در محیط Production این مقدار اجباری است چون در نبود آن، "
            "با هر ری‌استارت، تمام داده‌های رمزنگاری‌شده‌ی قبلی "
            "(نتایج آزمایش، کد ملی و...) غیرقابل‌بازیابی می‌شوند و "
            "به‌صورت متن نامفهوم به کاربر نمایش داده می‌شوند. "
            "اپلیکیشن متوقف شد.",
            flush=True
        )
        sys.exit(1)
    else:
        ENCRYPTION_KEY = Fernet.generate_key().decode("utf-8")
        print(
            "⚠️  ENCRYPTION_KEY تنظیم نشده — از یک کلید موقت تصادفی "
            "استفاده می‌شود (فقط برای محیط توسعه). داده‌های رمزنگاری‌شده "
            "با ری‌استارت سرور غیرقابل‌بازیابی می‌شوند.",
            flush=True
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

# ==========================
# Doctor license uploads
# ==========================

DOCTOR_DOCS_MAX_SIZE_MB = 10
DOCTOR_DOCS_ALLOWED_EXTENSIONS = [".pdf", ".png", ".jpg", ".jpeg"]

# ==========================
# Zarinpal payment gateway
# ==========================

ZARINPAL_MERCHANT_ID = os.getenv("ZARINPAL_MERCHANT_ID", "")
ZARINPAL_SANDBOX = os.getenv("ZARINPAL_SANDBOX", "true").strip().lower() == "true"

if not ZARINPAL_MERCHANT_ID:
    print("⚠️  ZARINPAL_MERCHANT_ID not set in .env — payments will fail until it's configured.")
# ==========================
# SMTP Settings (ایمیل واقعی)
# ==========================

SMTP_HOST = os.getenv("SMTP_HOST", "")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USER)
SMTP_USE_TLS = os.getenv("SMTP_USE_TLS", "true").strip().lower() == "true"

# ==========================
# Avatar uploads
# ==========================

AVATAR_MAX_SIZE_MB = 5
AVATAR_ALLOWED_EXTENSIONS = [".png", ".jpg", ".jpeg"]