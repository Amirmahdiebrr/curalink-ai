"""
app/core/security.py

Password hashing (bcrypt via passlib) and one-time-code (OTP) helpers.
"""

import secrets
import string
from datetime import datetime, timedelta

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(raw_password: str) -> str:
    return pwd_context.hash(raw_password)


def verify_password(raw_password: str, password_hash: str) -> bool:
    try:
        return pwd_context.verify(raw_password, password_hash)
    except Exception:
        return False


MIN_PASSWORD_LENGTH = 8


def validate_password_strength(raw_password: str) -> str | None:
    if not raw_password or len(raw_password) < MIN_PASSWORD_LENGTH:
        return f"رمز عبور باید حداقل {MIN_PASSWORD_LENGTH} کاراکتر باشد."

    has_letter = any(c.isalpha() for c in raw_password)
    has_digit = any(c.isdigit() for c in raw_password)

    if not (has_letter and has_digit):
        return "رمز عبور باید ترکیبی از حروف و عدد باشد."

    return None


OTP_LENGTH = 6
OTP_EXPIRY_MINUTES = 10
EMAIL_TOKEN_EXPIRY_HOURS = 24
RESET_TOKEN_EXPIRY_MINUTES = 30
MAX_VERIFY_ATTEMPTS = 5


def generate_otp_code() -> str:
    return "".join(secrets.choice(string.digits) for _ in range(OTP_LENGTH))


def generate_url_token() -> str:
    return secrets.token_urlsafe(32)


def hash_code(code: str) -> str:
    return pwd_context.hash(code)


def verify_code(code: str, code_hash: str) -> bool:
    try:
        return pwd_context.verify(code, code_hash)
    except Exception:
        return False


def otp_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=OTP_EXPIRY_MINUTES)


def email_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(hours=EMAIL_TOKEN_EXPIRY_HOURS)


def reset_token_expiry() -> datetime:
    return datetime.utcnow() + timedelta(minutes=RESET_TOKEN_EXPIRY_MINUTES)