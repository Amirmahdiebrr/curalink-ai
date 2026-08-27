"""
tests/test_auth_service.py

تست‌های حداقلی برای ثبت‌نام، ورود و اعتبارسنجی رمز عبور.
"""

import pytest

from app.services.auth_service import (
    register_patient,
    authenticate,
    AuthError,
    get_user_by_email,
)
from app.core.security import validate_password_strength


def test_validate_password_strength_rejects_short_password():
    error = validate_password_strength("abc1")
    assert error is not None


def test_validate_password_strength_rejects_letters_only():
    error = validate_password_strength("abcdefgh")
    assert error is not None


def test_validate_password_strength_accepts_valid_password():
    error = validate_password_strength("abcd1234")
    assert error is None


def test_register_patient_creates_user(db_session):
    user = register_patient(
        db_session,
        email="test@example.com",
        phone="09121234567",
        password="abcd1234",
        display_name="کاربر تست",
    )

    assert user.id is not None
    assert user.email == "test@example.com"
    assert user.is_active is True
    assert user.password_hash != "abcd1234"


def test_register_patient_rejects_duplicate_email(db_session):
    register_patient(
        db_session,
        email="dup@example.com",
        phone="09121111111",
        password="abcd1234",
        display_name="کاربر اول",
    )

    with pytest.raises(AuthError):
        register_patient(
            db_session,
            email="dup@example.com",
            phone="09122222222",
            password="abcd1234",
            display_name="کاربر دوم",
        )


def test_register_patient_rejects_duplicate_phone(db_session):
    register_patient(
        db_session,
        email="a@example.com",
        phone="09123334444",
        password="abcd1234",
        display_name="کاربر اول",
    )

    with pytest.raises(AuthError):
        register_patient(
            db_session,
            email="b@example.com",
            phone="09123334444",
            password="abcd1234",
            display_name="کاربر دوم",
        )


def test_authenticate_succeeds_with_correct_password(db_session):
    register_patient(
        db_session,
        email="login@example.com",
        phone="09129998888",
        password="abcd1234",
        display_name="کاربر ورود",
    )

    user = authenticate(db_session, email="login@example.com", password="abcd1234")

    assert user.email == "login@example.com"


def test_authenticate_fails_with_wrong_password(db_session):
    register_patient(
        db_session,
        email="wrongpass@example.com",
        phone="09127776666",
        password="abcd1234",
        display_name="کاربر رمز اشتباه",
    )

    with pytest.raises(AuthError):
        authenticate(db_session, email="wrongpass@example.com", password="wrongpassword")


def test_authenticate_fails_for_unknown_email(db_session):
    with pytest.raises(AuthError):
        authenticate(db_session, email="doesnotexist@example.com", password="abcd1234")


def test_get_user_by_email_normalizes_case(db_session):
    register_patient(
        db_session,
        email="Case@Example.com",
        phone="09125554444",
        password="abcd1234",
        display_name="کاربر بزرگ‌کوچک",
    )

    found = get_user_by_email(db_session, "case@example.com")

    assert found is not None
    assert found.email == "case@example.com"