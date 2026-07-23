"""
app/routers/auth.py

ثبت‌نام (انتخاب نوع حساب + بیمار/پزشک/سازمان)، ورود، خروج، پروفایل،
تایید ایمیل، تایید موبایل (OTP)، فراموشی رمز عبور — کاملاً مستقل از وردپرس.
"""

import uuid
from pathlib import Path

from fastapi import APIRouter, Request, Depends, Form, UploadFile, File, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import (
    register_patient,
    register_doctor,
    register_org,
    authenticate,
    AuthError,
    get_user_by_id,
    get_user_by_email,
    start_phone_verification,
    confirm_phone_otp,
    start_email_verification,
    confirm_email_token,
    start_password_reset,
    complete_password_reset,
)
from app.services.email_service import EmailService
from app.services.sms_service import SMSService
from app.services.file_service import signature_matches_extension
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.crypto import encrypt_value, decrypt_value
from app.core.limiter import limiter
from app.config import DOCTOR_DOCS_MAX_SIZE_MB, DOCTOR_DOCS_ALLOWED_EXTENSIONS


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

email_service = EmailService()
sms_service = SMSService()

DOCTOR_DOCS_DIR = Path("uploads/doctor_docs")
DOCTOR_DOCS_DIR.mkdir(parents=True, exist_ok=True)


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(db, user_id)


def _save_doctor_document(content: bytes, filename: str) -> str:
    """
    اعتبارسنجی و ذخیره‌ی فایل مدرک نظام پزشکی روی دیسک.
    در صورت نامعتبر بودن فرمت/حجم/محتوا، AuthError پرتاب می‌کند.
    """
    if not filename or not content:
        raise AuthError("فایل مدرک نظام پزشکی ارسال نشده است.")

    extension = Path(filename).suffix.lower()

    if extension not in DOCTOR_DOCS_ALLOWED_EXTENSIONS:
        raise AuthError("فرمت فایل مدرک نظام پزشکی مجاز نیست.")

    size_mb = len(content) / (1024 * 1024)

    if size_mb > DOCTOR_DOCS_MAX_SIZE_MB:
        raise AuthError(f"حجم فایل مدرک نباید بیشتر از {DOCTOR_DOCS_MAX_SIZE_MB} مگابایت باشد.")

    if not signature_matches_extension(extension, content):
        raise AuthError("محتوای فایل با پسوند اعلام‌شده مطابقت ندارد.")

    unique_name = f"{uuid.uuid4().hex}{extension}"
    filepath = DOCTOR_DOCS_DIR / unique_name

    with open(filepath, "wb") as f:
        f.write(content)

    return str(filepath)


# ==========================
# انتخاب نوع حساب (اولین قدم ثبت‌نام)
# ==========================

@router.get("/register")
async def register_choose_page(request: Request):
    return templates.TemplateResponse(
        request,
        "register_choose.html",
        {"request": request, "user": None}
    )


# ==========================
# ثبت‌نام (بیمار)
# ==========================

@router.get("/register/patient")
async def register_patient_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "register.html",
        {"request": request, "error": None, "csrf_token": csrf_token, "user": None}
    )


@router.post("/register/patient")
@limiter.limit("5/hour")
async def register_patient_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    display_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "register.html",
            {"request": request, "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.", "csrf_token": new_token, "user": None}
        )

    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"request": request, "error": "رمز عبور و تکرار آن یکسان نیستند.", "csrf_token": new_token, "user": None}
        )

    try:
        user = register_patient(
            db,
            email=email,
            phone=phone,
            password=password,
            display_name=display_name,
        )
    except AuthError as e:
        return templates.TemplateResponse(
            request,
            "register.html",
            {"request": request, "error": str(e), "csrf_token": new_token, "user": None}
        )

    # ارسال ایمیل تایید در پس‌زمینه (کاربر منتظر نمی‌ماند)
    try:
        verify_token = start_email_verification(db, user)
        background_tasks.add_task(email_service.send_email_verification, user.email, user.id, verify_token)
    except Exception as e:
        print(f"[Auth] Failed to queue verification email: {e}", flush=True)

    request.session["user_id"] = user.id

    return RedirectResponse(url="/billing/plans", status_code=303)


# ==========================
# ثبت‌نام (پزشک)
# ==========================

@router.get("/register/doctor")
async def register_doctor_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "register_doctor.html",
        {"request": request, "error": None, "csrf_token": csrf_token, "user": None}
    )


@router.post("/register/doctor")
async def register_doctor_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    display_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    specialty: str = Form(None),
    medical_council_no: str = Form(None),
    clinic_name: str = Form(None),
    license_document: UploadFile = File(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "register_doctor.html",
            {"request": request, "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.", "csrf_token": new_token, "user": None}
        )

    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "register_doctor.html",
            {"request": request, "error": "رمز عبور و تکرار آن یکسان نیستند.", "csrf_token": new_token, "user": None}
        )

    try:
        content = await license_document.read()
        license_path = _save_doctor_document(content, license_document.filename)
    except AuthError as e:
        return templates.TemplateResponse(
            request,
            "register_doctor.html",
            {"request": request, "error": str(e), "csrf_token": new_token, "user": None}
        )

    try:
        user = register_doctor(
            db,
            email=email,
            phone=phone,
            password=password,
            display_name=display_name,
            specialty=specialty,
            medical_council_no=medical_council_no,
            license_document_path=license_path,
            clinic_name=clinic_name,
        )
    except AuthError as e:
        return templates.TemplateResponse(
            request,
            "register_doctor.html",
            {"request": request, "error": str(e), "csrf_token": new_token, "user": None}
        )

    # پزشک تا تایید ادمین is_active=False است، پس اینجا لاگین خودکار نمی‌کنیم
    try:
        verify_token = start_email_verification(db, user)
        background_tasks.add_task(email_service.send_email_verification, user.email, user.id, verify_token)
    except Exception as e:
        print(f"[Auth] Failed to queue verification email (doctor): {e}", flush=True)

    return templates.TemplateResponse(
        request,
        "register_doctor_pending.html",
        {"request": request, "user": None}
    )


# ==========================
# ثبت‌نام (سازمان: کلینیک/آزمایشگاه/بیمارستان)
# ==========================

@router.get("/register/org")
async def register_org_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "register_org.html",
        {"request": request, "error": None, "csrf_token": csrf_token, "user": None}
    )


@router.post("/register/org")
@limiter.limit("5/hour")
async def register_org_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    display_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(...),
    password: str = Form(...),
    password_confirm: str = Form(...),
    org_name: str = Form(...),
    org_type: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "register_org.html",
            {"request": request, "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.", "csrf_token": new_token, "user": None}
        )

    if password != password_confirm:
        return templates.TemplateResponse(
            request,
            "register_org.html",
            {"request": request, "error": "رمز عبور و تکرار آن یکسان نیستند.", "csrf_token": new_token, "user": None}
        )

    if not org_name or not org_name.strip():
        return templates.TemplateResponse(
            request,
            "register_org.html",
            {"request": request, "error": "نام سازمان الزامی است.", "csrf_token": new_token, "user": None}
        )

    try:
        user = register_org(
            db,
            email=email,
            phone=phone,
            password=password,
            display_name=display_name,
            org_name=org_name.strip(),
            org_type=org_type or None,
        )
    except AuthError as e:
        return templates.TemplateResponse(
            request,
            "register_org.html",
            {"request": request, "error": str(e), "csrf_token": new_token, "user": None}
        )

    try:
        verify_token = start_email_verification(db, user)
        background_tasks.add_task(email_service.send_email_verification, user.email, user.id, verify_token)
    except Exception as e:
        print(f"[Auth] Failed to queue verification email (org): {e}", flush=True)

    request.session["user_id"] = user.id

    return RedirectResponse(url="/billing/plans", status_code=303)


# ==========================
# ورود
# ==========================

@router.get("/login")
async def login_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "error": None, "csrf_token": csrf_token, "user": None}
    )


@router.post("/login")
@limiter.limit("10/minute")
async def login_submit(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        print("[Auth] CSRF validation failed on /login", flush=True)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.", "csrf_token": new_token, "user": None}
        )

    try:
        user = authenticate(db, email=email, password=password)
    except AuthError as e:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": str(e), "csrf_token": new_token, "user": None}
        )

    request.session["user_id"] = user.id

    return RedirectResponse(url="/", status_code=303)


# ==========================
# خروج
# ==========================

@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


# ==========================
# تایید ایمیل
# ==========================

@router.get("/verify-email")
async def verify_email(request: Request, uid: int, token: str, db: Session = Depends(get_db)):

    user = get_user_by_id(db, uid)

    if not user:
        return templates.TemplateResponse(
            request,
            "verify_email.html",
            {"request": request, "success": False, "message": "کاربر پیدا نشد.", "user": None}
        )

    if user.email_verified:
        return templates.TemplateResponse(
            request,
            "verify_email.html",
            {"request": request, "success": True, "message": "ایمیل شما قبلاً تایید شده است.", "user": None}
        )

    ok = confirm_email_token(db, user, token)

    if ok:
        return templates.TemplateResponse(
            request,
            "verify_email.html",
            {"request": request, "success": True, "message": "ایمیل شما با موفقیت تایید شد.", "user": None}
        )

    return templates.TemplateResponse(
        request,
        "verify_email.html",
        {"request": request, "success": False, "message": "لینک تایید نامعتبر یا منقضی شده است.", "user": None}
    )


@router.post("/verify-email/resend")
async def resend_email_verification(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not user.email_verified:
        verify_token = start_email_verification(db, user)
        background_tasks.add_task(email_service.send_email_verification, user.email, user.id, verify_token)

    return RedirectResponse(url="/profile", status_code=303)


# ==========================
# تایید موبایل (OTP)
# ==========================

@router.get("/verify-phone")
async def verify_phone_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "verify_phone.html",
        {"request": request, "user": user, "csrf_token": csrf_token, "error": None, "sent": False}
    )


@router.post("/verify-phone/send")
@limiter.limit("5/hour")
async def verify_phone_send(
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "verify_phone.html",
            {"request": request, "user": user, "csrf_token": new_token, "error": "خطای اعتبارسنجی امنیتی.", "sent": False}
        )

    if user.phone_verified:
        return RedirectResponse(url="/profile", status_code=303)

    code = start_phone_verification(db, user)
    await sms_service.send_reminder(user.phone, f"کد تایید کیورالینک شما: {code}")

    return templates.TemplateResponse(
        request,
        "verify_phone.html",
        {"request": request, "user": user, "csrf_token": new_token, "error": None, "sent": True}
    )


@router.post("/verify-phone/verify")
@limiter.limit("10/hour")
async def verify_phone_verify(
    request: Request,
    code: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "verify_phone.html",
            {"request": request, "user": user, "csrf_token": new_token, "error": "خطای اعتبارسنجی امنیتی.", "sent": True}
        )

    ok = confirm_phone_otp(db, user, code.strip())

    if not ok:
        return templates.TemplateResponse(
            request,
            "verify_phone.html",
            {"request": request, "user": user, "csrf_token": new_token, "error": "کد وارد شده اشتباه یا منقضی شده است.", "sent": True}
        )

    return RedirectResponse(url="/profile", status_code=303)


# ==========================
# فراموشی رمز عبور
# ==========================

@router.get("/forgot-password")
async def forgot_password_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"request": request, "csrf_token": csrf_token, "error": None, "sent": False, "user": None}
    )


@router.post("/forgot-password")
@limiter.limit("5/hour")
async def forgot_password_submit(
    request: Request,
    background_tasks: BackgroundTasks,
    email: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "forgot_password.html",
            {"request": request, "csrf_token": new_token, "error": "خطای اعتبارسنجی امنیتی.", "sent": False, "user": None}
        )

    user = get_user_by_email(db, email)

    if user:
        reset_token = start_password_reset(db, user)
        background_tasks.add_task(email_service.send_password_reset, user.email, user.id, reset_token)

    # پیام یکسان چه ایمیل ثبت‌شده باشد چه نباشد (جلوگیری از لو رفتن ایمیل‌های ثبت‌شده)
    return templates.TemplateResponse(
        request,
        "forgot_password.html",
        {"request": request, "csrf_token": new_token, "error": None, "sent": True, "user": None}
    )


@router.get("/reset-password")
async def reset_password_page(request: Request, uid: int, token: str):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "reset_password.html",
        {"request": request, "csrf_token": csrf_token, "error": None, "uid": uid, "token": token, "user": None}
    )


@router.post("/reset-password")
async def reset_password_submit(
    request: Request,
    uid: int = Form(...),
    token: str = Form(...),
    new_password: str = Form(...),
    new_password_confirm: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"request": request, "csrf_token": new_token, "error": "خطای اعتبارسنجی امنیتی.", "uid": uid, "token": token, "user": None}
        )

    if new_password != new_password_confirm:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"request": request, "csrf_token": new_token, "error": "رمز عبور و تکرار آن یکسان نیستند.", "uid": uid, "token": token, "user": None}
        )

    user = get_user_by_id(db, uid)

    if not user:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"request": request, "csrf_token": new_token, "error": "لینک نامعتبر است.", "uid": uid, "token": token, "user": None}
        )

    try:
        complete_password_reset(db, user, token, new_password)
    except AuthError as e:
        return templates.TemplateResponse(
            request,
            "reset_password.html",
            {"request": request, "csrf_token": new_token, "error": str(e), "uid": uid, "token": token, "user": None}
        )

    return RedirectResponse(url="/login", status_code=303)


# ==========================
# پروفایل
# ==========================

@router.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    csrf_token = get_or_create_csrf_token(request)

    decrypted_national_id = decrypt_value(user.national_id)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "national_id_display": decrypted_national_id,
            "saved": False,
            "error": None,
            "csrf_token": csrf_token,
        }
    )


@router.post("/profile")
async def profile_update(
    request: Request,
    display_name: str = Form(None),
    age: str = Form(None),
    gender: str = Form(None),
    national_id: str = Form(None),
    address: str = Form(None),
    phone: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    new_token = get_or_create_csrf_token(request)

    if not is_valid_csrf(request, csrf_token):
        print("[Auth] CSRF validation failed on /profile", flush=True)
        return templates.TemplateResponse(
            request,
            "profile.html",
            {
                "request": request,
                "user": user,
                "national_id_display": decrypt_value(user.national_id),
                "saved": False,
                "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.",
                "csrf_token": new_token,
            }
        )

    if display_name and display_name.strip():
        user.display_name = display_name.strip()

    if age and age.isdigit():
        age_value = int(age)
        if 0 <= age_value <= 120:
            user.age = age_value
        else:
            return templates.TemplateResponse(
                request,
                "profile.html",
                {
                    "request": request,
                    "user": user,
                    "national_id_display": decrypt_value(user.national_id),
                    "saved": False,
                    "error": "سن وارد شده معتبر نیست.",
                    "csrf_token": new_token,
                }
            )
    else:
        user.age = None

    user.gender = gender or None
    user.national_id = encrypt_value(national_id.strip()) if national_id and national_id.strip() else None
    user.address = address or None

    if phone and phone.strip() and phone.strip() != user.phone:
        new_phone = phone.strip()

        existing = db.query(User).filter(User.phone == new_phone, User.id != user.id).first()

        if existing:
            return templates.TemplateResponse(
                request,
                "profile.html",
                {
                    "request": request,
                    "user": user,
                    "national_id_display": decrypt_value(user.national_id),
                    "saved": False,
                    "error": "این شماره موبایل قبلاً توسط حساب دیگری ثبت شده است.",
                    "csrf_token": new_token,
                }
            )

        user.phone = new_phone
        user.phone_verified = False  # شماره جدید، تا وقتی OTP نشده تایید‌نشده است

    db.commit()
    db.refresh(user)

    new_token2 = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "national_id_display": decrypt_value(user.national_id),
            "saved": True,
            "error": None,
            "csrf_token": new_token2,
        }
    )