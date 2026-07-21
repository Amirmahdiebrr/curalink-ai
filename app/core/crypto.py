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

from cryptography.fernet import Fernet, InvalidToken

from app.config import ENCRYPTION_KEY


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
        print("[Crypto] Failed to decrypt value, returning as legacy plaintext.", flush=True)
        return value