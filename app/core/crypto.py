"""
app/core/crypto.py

Symmetric encryption helper for sensitive personal fields (e.g. national_id)
stored in the local database. Uses Fernet (AES-128 in CBC mode + HMAC)
from the `cryptography` package.

Values are encrypted before being written to the database and decrypted
only when needed for display. If decryption fails (e.g. legacy plaintext
data saved before this was introduced), the raw value is returned as-is
so existing data isn't lost; it will be re-encrypted on the next save.
"""

import hmac
import hashlib

from cryptography.fernet import Fernet, InvalidToken

from app.config import ENCRYPTION_KEY, SESSION_SECRET_KEY
from app.core.logging_config import get_logger

logger = get_logger(__name__)

_fernet = Fernet(ENCRYPTION_KEY)

# Fernet ciphertext همیشه با این رشته (نسخه‌ی توکن، base64) شروع می‌شود
# و برخلاف متن ساده، شامل کاراکترهای غیرقابل‌چاپ/پترن base64 است؛
# از این برای تشخیص «قبلاً رمزنگاری شده یا نه» استفاده می‌کنیم.
_ENCRYPTED_PREFIX = "gAAAAA"


def encrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    return _fernet.encrypt(value.encode("utf-8")).decode("utf-8")


def decrypt_value(value: str | None) -> str | None:
    if value is None or value == "":
        return None

    try:
        return _fernet.decrypt(value.encode("utf-8")).decode("utf-8")
    except (InvalidToken, ValueError):
        # داده‌ی قدیمی که هنوز رمزنگاری نشده (قبل از این تغییر)؛
        # همان‌طور که هست نمایش می‌دهیم تا داده گم نشود.
        logger.warning("[Crypto] Failed to decrypt value, returning as legacy plaintext.")
        return value


_HASH_KEY = (SESSION_SECRET_KEY or "").encode("utf-8")


def hash_national_id(national_id: str | None) -> str | None:
    """
    یک هش یک‌طرفه و قطعی (HMAC-SHA256) از کد ملی تولید می‌کند که برای
    جستجو/ورود استفاده می‌شود (چون خودِ national_id با Fernet رمزنگاری
    می‌شود و رمزنگاری Fernet هر بار خروجی متفاوتی تولید می‌کند، پس
    قابل جستجوی مستقیم در دیتابیس نیست). این تابع فقط یک عدد ثابت
    برمی‌گرداند، نه چیزی که بشود از آن کد ملی اصلی را بازیابی کرد.
    """
    if not national_id:
        return None

    normalized = national_id.strip()

    if not normalized:
        return None

    return hmac.new(_HASH_KEY, normalized.encode("utf-8"), hashlib.sha256).hexdigest()


def normalize_national_id(national_id: str | None) -> str | None:
    """
    کد ملی وارد‌شده را تمیز می‌کند (فقط ارقام، بدون فاصله/خط‌تیره).
    اعتبارسنجی دقیق (الگوریتم چک‌دیجیت) عمداً انجام نمی‌شود تا فرآیند
    ثبت‌نام ساده و روان بماند؛ فقط طول و رقمی‌بودن بررسی می‌شود.
    """
    if not national_id:
        return None

    digits = "".join(ch for ch in national_id.strip() if ch.isdigit())

    if len(digits) != 10:
        return None

    return digits