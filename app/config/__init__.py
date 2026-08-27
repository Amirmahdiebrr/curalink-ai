from dotenv import load_dotenv
import os
import sys
import secrets
from pathlib import Path

from cryptography.fernet import Fernet

BASE_DIR = Path(__file__).resolve().parent.parent.parent
ENV_FILE = BASE_DIR / ".env"
load_dotenv(ENV_FILE)

# ==========================
# اعتبارسنجی زودهنگام متغیرهای محیطی با pydantic-settings.
# اگر مقداری نامعتبر باشد (مثلاً SMTP_PORT خارج از بازه، یا
# EMAIL_PROVIDER با مقدار ناشناخته)، همین‌جا با پیام خطای واضح
# برنامه متوقف می‌شود، نه وسط پردازش یک درخواست واقعی.
# ==========================

from app.config.settings import load_validated_settings

_validated = load_validated_settings()

AI_PROVIDER = os.getenv(
    "AI_PROVIDER",
    "nvidia"
)

AI_MODEL = os.getenv(
    "AI_MODEL",
    "deepseek-ai/deepseek-v4-pro"
)

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
# GapGPT API Settings
# ==========================

GAPGPT_API_KEY = os.getenv("GAPGPT_API_KEY")
GAPGPT_BASE_URL = os.getenv("GAPGPT_BASE_URL", "https://api.gapgpt.app/v1")

if GAPGPT_API_KEY:
    print("✅ GAPGPT API KEY loaded")
else:
    print("❌ GAPGPT API KEY missing")

# ==========================
# آدرس پایه سایت - باید قبل از چک production تعریف بشه
# ==========================

APP_BASE_URL = os.getenv("APP_BASE_URL", "http://localhost:8000")

IS_PRODUCTION = APP_BASE_URL.startswith("https://")

# ==========================
# دیتابیس
#
# اگر DATABASE_URL در .env تنظیم شده باشد (مثلاً یک آدرس PostgreSQL
# مثل postgresql://user:pass@host:5432/dbname)، همان استفاده می‌شود.
# در غیر این صورت (پیش‌فرض محیط توسعه)، از همان فایل SQLite قبلی
# استفاده می‌شود تا هیچ‌کس مجبور به نصب PostgreSQL برای توسعه‌ی محلی
# نباشد.
# ==========================

DATABASE_URL = os.getenv("DATABASE_URL", "").strip()

if not DATABASE_URL:
    _data_dir = BASE_DIR / "data"
    _data_dir.mkdir(exist_ok=True)
    DATABASE_URL = f"sqlite:///{_data_dir}/lab_analyzer.db"
    print("ℹ️  DATABASE_URL تنظیم نشده — از SQLite محلی استفاده می‌شود (فقط مناسب توسعه).")
else:
    print(f"✅ DATABASE_URL از .env خوانده شد: {DATABASE_URL.split('@')[-1] if '@' in DATABASE_URL else DATABASE_URL}")

if IS_PRODUCTION and DATABASE_URL.startswith("sqlite"):
    print(
        "⚠️  هشدار: در APP_BASE_URL با https (یعنی حالت production) هستید "
        "ولی هنوز از SQLite استفاده می‌کنید. برای مقیاس‌پذیری و جلوگیری از "
        "قفل‌شدن دیتابیس زیر بار همزمان چند worker، مهاجرت به PostgreSQL "
        "توصیه می‌شود (متغیر DATABASE_URL را در .env تنظیم کنید)."
    )

# ==========================
# SESSION_SECRET_KEY و ENCRYPTION_KEY
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