"""
app/routers/auth.py

ثبت‌نام، ورود، خروج و پروفایل کاربر — کاملاً مستقل از وردپرس.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import User
from app.services.auth_service import (
    register_patient,
    authenticate,
    AuthError,
    get_user_by_id,
)
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.crypto import encrypt_value, decrypt_value


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    return get_user_by_id(db, user_id)


# ==========================
# ثبت‌نام
# ==========================

@router.get("/register")
async def register_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "register.html",
        {"request": request, "error": None, "csrf_token": csrf_token, "user": None}
    )


@router.post("/register")
async def register_submit(
    request: Request,
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

    request.session["user_id"] = user.id

    return RedirectResponse(url="/", status_code=303)


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

    user.age = int(age) if age and age.isdigit() else None
    user.gender = gender or None
    user.national_id = encrypt_value(national_id.strip()) if national_id and national_id.strip() else None
    user.address = address or None

    if phone and phone.strip() and phone.strip() != user.phone:
        user.phone = phone.strip()
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