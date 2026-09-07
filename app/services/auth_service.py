"""
app/services/auth_service.py

سرویس مستقل احراز هویت: ثبت‌نام بیمار/پزشک/سازمان، ورود بر اساس کد
ملی، OTP موبایل، تایید ایمیل (اختیاری)، بازیابی رمز عبور، و مدیریت
ادمین‌های پلتفرم (ارتقا/عزل/مستر).
"""

from datetime import datetime

from sqlalchemy.orm import Session

from app.models import (
    User, DoctorProfile, OrganizationProfile, VerificationCode,
    ROLE_PATIENT, ROLE_DOCTOR, ROLE_ORG_ADMIN, ROLE_PLATFORM_ADMIN,
    VERIFICATION_PENDING, VERIFICATION_APPROVED, VERIFICATION_REJECTED,
)
from app.core.security import (
    hash_password, verify_password, validate_password_strength,
    generate_otp_code, generate_url_token, hash_code, verify_code,
    otp_expiry, email_token_expiry, reset_token_expiry,
    MAX_VERIFY_ATTEMPTS, generate_url_token as _gen_token,
)
from app.core.crypto import encrypt_value, hash_national_id, normalize_national_id
import secrets
import string


class AuthError(Exception):
    pass


def get_user_by_email(db: Session, email: str) -> User | None:
    email = (email or "").strip().lower()
    if not email:
        return None
    return db.query(User).filter(User.email == email).first()


def get_user_by_phone(db: Session, phone: str) -> User | None:
    phone = (phone or "").strip()
    return db.query(User).filter(User.phone == phone).first()


def get_user_by_id(db: Session, user_id: int) -> User | None:
    return db.query(User).filter(User.id == user_id).first()


def get_user_by_national_id(db: Session, national_id: str) -> User | None:
    normalized = normalize_national_id(national_id)

    if not normalized:
        return None

    national_id_hash = hash_national_id(normalized)
    return db.query(User).filter(User.national_id_hash == national_id_hash).first()


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


def register_patient(db: Session, national_id: str, phone: str, password: str, display_name: str, email: str | None = None) -> User:
    return _register_common(db, national_id=national_id, email=email, phone=phone, password=password, display_name=display_name, role=ROLE_PATIENT)


def register_doctor(
    db: Session, national_id: str, phone: str, password: str, display_name: str,
    specialty: str | None, medical_council_no: str | None,
    license_document_path: str | None, clinic_name: str | None = None,
    email: str | None = None,
) -> User:
    user = _register_common(db, national_id=national_id, email=email, phone=phone, password=password, display_name=display_name, role=ROLE_DOCTOR)

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


def register_org(
    db: Session, national_id: str, phone: str, password: str, display_name: str,
    org_name: str, org_type: str | None = None, email: str | None = None,
) -> User:
    user = _register_common(db, national_id=national_id, email=email, phone=phone, password=password, display_name=display_name, role=ROLE_ORG_ADMIN)

    profile = OrganizationProfile(
        user_id=user.id,
        org_name=org_name,
        org_type=org_type,
    )
    db.add(profile)
    db.commit()
    db.refresh(user)

    return user


def _register_common(db: Session, national_id: str, email: str | None, phone: str, password: str, display_name: str, role: str) -> User:

    email = (email or "").strip().lower() or None
    phone = (phone or "").strip()
    display_name = (display_name or "").strip()

    normalized_national_id = normalize_national_id(national_id)

    if not normalized_national_id:
        raise AuthError("کد ملی معتبر (۱۰ رقم) وارد کنید.")

    if not phone:
        raise AuthError("شماره موبایل الزامی است.")

    if not display_name:
        raise AuthError("نام و نام خانوادگی الزامی است.")

    password_error = validate_password_strength(password)
    if password_error:
        raise AuthError(password_error)

    if email and "@" not in email:
        raise AuthError("ایمیل وارد‌شده معتبر نیست.")

    if email and get_user_by_email(db, email):
        raise AuthError("این ایمیل قبلاً ثبت شده است.")

    if get_user_by_phone(db, phone):
        raise AuthError("این شماره موبایل قبلاً ثبت شده است.")

    national_id_hash = hash_national_id(normalized_national_id)

    if db.query(User).filter(User.national_id_hash == national_id_hash).first():
        raise AuthError("این کد ملی قبلاً ثبت شده است.")

    user = User(
        role=role,
        email=email,
        password_hash=hash_password(password),
        phone=phone,
        display_name=display_name,
        national_id=encrypt_value(normalized_national_id),
        national_id_hash=national_id_hash,
        is_active=True,
        email_verified=False,
        phone_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    return user


def authenticate(db: Session, national_id: str, password: str) -> User:

    user = get_user_by_national_id(db, national_id)

    if not user or not verify_password(password, user.password_hash):
        raise AuthError("کد ملی یا رمز عبور اشتباه است.")

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


def set_national_id(db: Session, user: User, national_id: str | None) -> None:
    if not national_id or not national_id.strip():
        user.national_id = None
        user.national_id_hash = None
        db.commit()
        return

    normalized = normalize_national_id(national_id)

    if not normalized:
        raise AuthError("کد ملی وارد‌شده معتبر نیست.")

    national_id_hash = hash_national_id(normalized)

    existing = (
        db.query(User)
        .filter(User.national_id_hash == national_id_hash, User.id != user.id)
        .first()
    )

    if existing:
        raise AuthError("این کد ملی قبلاً توسط حساب دیگری ثبت شده است.")

    user.national_id = encrypt_value(normalized)
    user.national_id_hash = national_id_hash
    db.commit()


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


def change_email(db: Session, user: User, new_email: str, current_password: str) -> None:
    new_email = (new_email or "").strip().lower()

    if not verify_password(current_password, user.password_hash):
        raise AuthError("رمز عبور فعلی اشتباه است.")

    if not new_email:
        user.email = None
        user.email_verified = False
        db.commit()
        return

    if "@" not in new_email:
        raise AuthError("ایمیل معتبر وارد کنید.")

    if get_user_by_email(db, new_email) and new_email != user.email:
        raise AuthError("این ایمیل قبلاً توسط حساب دیگری ثبت شده است.")

    user.email = new_email
    user.email_verified = False
    db.commit()


def change_password(db: Session, user: User, current_password: str, new_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("رمز عبور فعلی اشتباه است.")

    password_error = validate_password_strength(new_password)
    if password_error:
        raise AuthError(password_error)

    user.password_hash = hash_password(new_password)
    db.commit()


def update_avatar(db: Session, user: User, avatar_path: str) -> None:
    user.avatar_path = avatar_path
    db.commit()


def delete_own_account(db: Session, user: User, current_password: str) -> None:
    if not verify_password(current_password, user.password_hash):
        raise AuthError("رمز عبور اشتباه است.")

    db.delete(user)
    db.commit()


def admin_delete_user(db: Session, user_id: int) -> User:
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise AuthError("کاربر پیدا نشد.")

    db.delete(user)
    db.commit()

    return user


# ==========================
# مدیریت ادمین‌های پلتفرم (فقط ادمین مستر)
# ==========================

def get_all_platform_admins(db: Session):
    return (
        db.query(User)
        .filter(User.role == ROLE_PLATFORM_ADMIN)
        .order_by(User.is_super_admin.desc(), User.created_at.asc())
        .all()
    )


def find_user_by_identifier(db: Session, identifier: str) -> User | None:
    """
    جستجوی کاربر برای ارتقا به ادمین، بر اساس ایمیل، شماره موبایل یا آیدی عددی.
    """
    identifier = (identifier or "").strip()

    if not identifier:
        return None

    if identifier.isdigit():
        by_id = db.query(User).filter(User.id == int(identifier)).first()
        if by_id:
            return by_id

    by_phone = get_user_by_phone(db, identifier)
    if by_phone:
        return by_phone

    return get_user_by_email(db, identifier)


def promote_to_platform_admin(db: Session, user_id: int) -> User:
    user = get_user_by_id(db, user_id)

    if not user:
        raise AuthError("کاربر پیدا نشد.")

    if user.role == ROLE_PLATFORM_ADMIN:
        raise AuthError("این کاربر از قبل ادمین پلتفرم است.")

    user.role = ROLE_PLATFORM_ADMIN
    user.is_active = True
    user.verification_status = None

    db.commit()
    db.refresh(user)

    return user


def demote_platform_admin(db: Session, admin_id: int, acting_user_id: int) -> User:
    admin = get_user_by_id(db, admin_id)

    if not admin or admin.role != ROLE_PLATFORM_ADMIN:
        raise AuthError("ادمین مورد نظر پیدا نشد.")

    if admin.id == acting_user_id:
        raise AuthError("نمی‌توانید خودتان را عزل کنید.")

    if admin.is_super_admin:
        raise AuthError("نمی‌توانید ادمین مستر را عزل کنید؛ ابتدا وضعیت مستر را از او بگیرید.")

    admin.role = ROLE_PATIENT
    admin.is_super_admin = False

    db.commit()
    db.refresh(admin)

    return admin


def set_super_admin(db: Session, admin_id: int, value: bool, acting_user_id: int) -> User:
    admin = get_user_by_id(db, admin_id)

    if not admin or admin.role != ROLE_PLATFORM_ADMIN:
        raise AuthError("ادمین مورد نظر پیدا نشد.")

    if not value and admin.id == acting_user_id:
        raise AuthError("نمی‌توانید وضعیت مستر بودن خودتان را حذف کنید. ابتدا شخص دیگری را مستر کنید.")

    admin.is_super_admin = value
    db.commit()
    db.refresh(admin)

    return admin


def admin_reset_password(db: Session, target_user_id: int) -> tuple[User, str]:
    """
    یک رمز عبور تصادفی جدید برای کاربر تولید و ذخیره می‌کند (هش‌شده).
    رمز خام فقط یک‌بار در همین بازگشت مقدار در دسترس است و در دیتابیس
    ذخیره نمی‌شود، چون رمزها فقط به‌صورت هش (bcrypt، یک‌طرفه) نگه‌داری
    می‌شوند و امکان بازیابی متن اصلی رمز قبلی وجود ندارد.
    """
    user = get_user_by_id(db, target_user_id)

    if not user:
        raise AuthError("کاربر پیدا نشد.")

    alphabet = string.ascii_letters + string.digits
    new_password = "".join(secrets.choice(alphabet) for _ in range(12))

    user.password_hash = hash_password(new_password)
    db.commit()
    db.refresh(user)

    return user, new_password