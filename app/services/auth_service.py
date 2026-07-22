"""
app/services/auth_service.py

سرویس مستقل احراز هویت: ثبت‌نام بیمار/پزشک، ورود، OTP موبایل،
تایید ایمیل، بازیابی رمز عبور.
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    User, DoctorProfile, VerificationCode,
    ROLE_PATIENT, ROLE_DOCTOR,
    VERIFICATION_PENDING, VERIFICATION_APPROVED, VERIFICATION_REJECTED,
)
from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    generate_otp_code, generate_url_token, hash_code, verify_code,
    otp_expiry, email_token_expiry, reset_token_expiry,
    MAX_VERIFY_ATTEMPTS,
)


class AuthError(Exception):
    pass


def get_user_by_email(db: Session, email: str) -> User | None:
    email = (email or "").strip().lower()
    return db.query(User).filter(User.email == email).first()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    phone = (phone or "").strip()
    return db.query(User).filter(User.phone == phone).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def _create_verification_code(db: Session, user_id: int, purpose: str, raw_code: str, expires_at) -> None:
    record = VerificationCode(
        user_id=user_id,
        purpose=purpose,
        code_hash=hash_code(raw_code),
        expires_at=expires_at,
    )
    db.add(record)
    db.commit()


def _consume_valid_code(db: Session, user_id: int, purpose: str, submitted_code: str) -> bool:
    record = (
        db.query(VerificationCode)
        .filter(
            VerificationCode.user_id == user_id,
            VerificationCode.purpose == purpose,
            VerificationCode.used_at.is_(None),
        )
        .order_by(VerificationCode.created_at.desc())
        .first()
    )

    if not record:
        return False

    if record.expires_at < datetime.utcnow():
        return False

    if record.attempts >= MAX_VERIFY_ATTEMPTS:
        return False

    record.attempts += 1

    if not verify_code(submitted_code, record.code_hash):
        db.commit()
        return False

    record.used_at = datetime.utcnow()
    db.commit()
    return True


def register_patient(db: Session, email: str, phone: str, password: str, display_name: str) -> User:
    return _register_common(db, email=email, phone=phone, password=password, display_name=display_name, role=ROLE_PATIENT)


def register_doctor(
    db: Session, email: str, phone: str, password: str, display_name: str,
    specialty: str | None, medical_council_no: str | None,
    license_document_path: str | None, clinic_name: str | None = None,
) -> User:
    user = _register_common(db, email=email, phone=phone, password=password, display_name=display_name, role=ROLE_DOCTOR)

    user.verification_status = VERIFICATION_PENDING
    user.is_active = False

    profile = DoctorProfile(
        user_id=user.id,
        specialty=specialty,
        medical_council_no=medical_council_no,
        license_document_path=license_document_path,
        clinic_name=clinic_name,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    return user


def _register_common(db: Session, email: str, phone: str, password: str, display_name: str, role: str) -> User:

    email = (email or "").strip().lower()
    phone = (phone or "").strip()
    display_name = (display_name or "").strip()

    if not email or "@" not in email:
        raise AuthError("ایمیل معتبر وارد کنید.")

    if not phone:
        raise AuthError("شماره موبایل الزامی است.")

    if not display_name:
        raise AuthError("نام و نام خانوادگی الزامی است.")

    password_error = validate_password_strength(password)
    if password_error:
        raise AuthError(password_error)

    if get_user_by_email(db, email):
        raise AuthError("این ایمیل قبلاً ثبت شده است.")

    if get_user_by_phone(db, phone):
        raise AuthError("این شماره موبایل قبلاً ثبت شده است.")

    user = User(
        role=role,
        email=email,
        password_hash=hash_password(password),
        phone=phone,
        display_name=display_name,
        is_active=True,
        email_verified=False,
        phone_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate(db: Session, email: str, password: str) -> User:

    user = get_user_by_email(db, email)

    if not user or not verify_password(password, user.password_hash):
        raise AuthError("ایمیل یا رمز عبور اشتباه است.")

    if not user.is_active:
        if user.verification_status == VERIFICATION_PENDING:
            raise AuthError("حساب شما هنوز توسط ادمین تایید نشده است.")
        if user.verification_status == "rejected":
            raise AuthError("متاسفانه درخواست شما تایید نشد. برای اطلاعات بیشتر با پشتیبانی تماس بگیرید.")
        raise AuthError("این حساب غیرفعال است.")

    user.last_login_at = datetime.utcnow()
    db.commit()
    db.refresh(user)

    return user


def start_phone_verification(db: Session, user: User) -> str:
    code = generate_otp_code()
    _create_verification_code(db, user.id, "phone_otp", code, otp_expiry())
    return code


def confirm_phone_otp(db: Session, user: User, submitted_code: str) -> bool:
    ok = _consume_valid_code(db, user.id, "phone_otp", submitted_code)
    if ok:
        user.phone_verified = True
        db.commit()
    return ok


def start_email_verification(db: Session, user: User) -> str:
    token = generate_url_token()
    _create_verification_code(db, user.id, "email_verify", token, email_token_expiry())
    return token


def confirm_email_token(db: Session, user: User, submitted_token: str) -> bool:
    ok = _consume_valid_code(db, user.id, "email_verify", submitted_token)
    if ok:
        user.email_verified = True
        db.commit()
    return ok


def start_password_reset(db: Session, user: User) -> str:
    token = generate_url_token()
    _create_verification_code(db, user.id, "password_reset", token, reset_token_expiry())
    return token


def complete_password_reset(db: Session, user: User, submitted_token: str, new_password: str) -> None:
    if not _consume_valid_code(db, user.id, "password_reset", submitted_token):
        raise AuthError("لینک بازیابی رمز عبور نامعتبر یا منقضی شده است.")

    password_error = validate_password_strength(new_password)
    if password_error:
        raise AuthError(password_error)

    user.password_hash = hash_password(new_password)
    db.commit()
def get_pending_doctors(db: Session):
    return (
        db.query(User)
        .filter(User.role == ROLE_DOCTOR, User.verification_status == VERIFICATION_PENDING)
        .order_by(User.created_at.desc())
        .all()
    )


def get_reviewed_doctors(db: Session):
    return (
        db.query(User)
        .filter(
            User.role == ROLE_DOCTOR,
            User.verification_status.in_([VERIFICATION_APPROVED, VERIFICATION_REJECTED]),
        )
        .order_by(User.created_at.desc())
        .all()
    )


def approve_doctor(db: Session, doctor_id: int, admin_id: int) -> User:
    doctor = db.query(User).filter(User.id == doctor_id, User.role == ROLE_DOCTOR).first()

    if not doctor:
        raise AuthError("پزشک مورد نظر پیدا نشد.")

    doctor.verification_status = VERIFICATION_APPROVED
    doctor.is_active = True

    if doctor.doctor_profile:
        doctor.doctor_profile.reviewed_at = datetime.utcnow()
        doctor.doctor_profile.reviewed_by_user_id = admin_id

    db.commit()
    db.refresh(doctor)

    return doctor


def reject_doctor(db: Session, doctor_id: int, admin_id: int, note: str | None = None) -> User:
    doctor = db.query(User).filter(User.id == doctor_id, User.role == ROLE_DOCTOR).first()

    if not doctor:
        raise AuthError("پزشک مورد نظر پیدا نشد.")

    doctor.verification_status = VERIFICATION_REJECTED
    doctor.is_active = False
    doctor.verification_note = note

    if doctor.doctor_profile:
        doctor.doctor_profile.reviewed_at = datetime.utcnow()
        doctor.doctor_profile.reviewed_by_user_id = admin_id

    db.commit()
    db.refresh(doctor)

    return doctor