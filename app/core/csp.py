"""
app/core/csp.py

CSP nonce زیرساخت: هر ریکوئست یک nonce تصادفی می‌گیرد که هم در هدر
Content-Security-Policy و هم در تگ‌های <script> اینلاین تمپلیت‌ها
استفاده می‌شود، تا فقط اسکریپت‌های خودمان (نه اسکریپت تزریق‌شده توسط
مهاجم) مجاز به اجرا باشند.
"""

import secrets
from contextvars import ContextVar

_csp_nonce: ContextVar[str] = ContextVar("csp_nonce", default="")


def generate_nonce() -> str:
    return secrets.token_urlsafe(16)


def set_nonce(nonce: str) -> None:
    _csp_nonce.set(nonce)


def get_nonce() -> str:
    return _csp_nonce.get()