"""
app/config/settings.py

اعتبارسنجی متغیرهای محیطی با pydantic-settings. برخلاف os.getenv
دستی، اگر یک مقدار الزامی خالی باشد یا نوع اشتباهی داشته باشد،
برنامه همان لحظه‌ی استارت با یک پیام خطای واضح متوقف می‌شود، نه
وسط پردازش یک درخواست واقعی کاربر.

این فایل موازی با app/config/__init__.py (که بقیه‌ی کد پروژه از آن
مقدار می‌خواند) اجرا می‌شود؛ صرفاً یک لایه‌ی اعتبارسنجی زودهنگام
اضافه می‌کند و مقادیر نهایی هنوز از همان app/config/__init__.py
خوانده می‌شوند تا امضای import در بقیه‌ی پروژه تغییر نکند.
"""

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # ===== AI =====
    AI_PROVIDER: str = "nvidia"
    AI_MODEL: str = "deepseek-ai/deepseek-v4-pro"
    AI_FALLBACK_MODEL: str = "deepseek-ai/deepseek-v4-flash"

    NVIDIA_API_KEY: str | None = None
    GAPGPT_API_KEY: str | None = None
    GAPGPT_BASE_URL: str = "https://api.gapgpt.app/v1"

    # ===== App =====
    APP_BASE_URL: str = "http://localhost:8000"

    # ===== Secrets =====
    SESSION_SECRET_KEY: str | None = None
    ENCRYPTION_KEY: str | None = None

    # ===== SMS / Email =====
    SMS_PROVIDER: str = "console"
    EMAIL_PROVIDER: str = "console"

    # ===== Zarinpal =====
    ZARINPAL_MERCHANT_ID: str = ""
    ZARINPAL_SANDBOX: bool = True

    # ===== SMTP =====
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_USE_TLS: bool = True

    # ===== OCR =====
    TESSERACT_CMD: str | None = None

    @field_validator("SMTP_PORT")
    @classmethod
    def validate_smtp_port(cls, v: int) -> int:
        if not (1 <= v <= 65535):
            raise ValueError(f"SMTP_PORT باید بین ۱ تا ۶۵۵۳۵ باشد، مقدار دریافتی: {v}")
        return v

    @field_validator("EMAIL_PROVIDER")
    @classmethod
    def validate_email_provider(cls, v: str) -> str:
        allowed = {"console", "smtp"}
        if v not in allowed:
            raise ValueError(f"EMAIL_PROVIDER باید یکی از {allowed} باشد، مقدار دریافتی: '{v}'")
        return v

    @field_validator("SMS_PROVIDER")
    @classmethod
    def validate_sms_provider(cls, v: str) -> str:
        allowed = {"console"}
        if v not in allowed:
            raise ValueError(f"SMS_PROVIDER باید یکی از {allowed} باشد، مقدار دریافتی: '{v}'")
        return v


def load_validated_settings() -> AppSettings:
    """
    تلاش می‌کند تنظیمات را از .env بخواند و اعتبارسنجی کند. اگر چیزی
    نامعتبر باشد، پیام خطای دقیق pydantic را چاپ می‌کند و سپس همان
    exception اصلی را دوباره raise می‌کند تا استارت برنامه متوقف شود.
    """
    try:
        return AppSettings()
    except Exception as e:
        print("=" * 60, flush=True)
        print("❌ FATAL: متغیرهای محیطی نامعتبر هستند.", flush=True)
        print(str(e), flush=True)
        print("=" * 60, flush=True)
        raise