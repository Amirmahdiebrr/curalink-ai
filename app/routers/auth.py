"""
app/routers/auth.py

Login (via WordPress JWT), logout, and local profile routes.
Account creation/registration happens on the main WordPress site,
not in this app.
"""

from fastapi import APIRouter, Request, Depends, Form
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import LocalUser
from app.services.auth_service import get_or_create_user
from app.services.wp_auth_service import login_with_wordpress, WPAuthError
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.crypto import encrypt_value, decrypt_value


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("local_user_id")
    if not user_id:
        return None
    return db.query(LocalUser).filter(LocalUser.id == user_id).first()


@router.get("/login")
async def login_page(request: Request):
    csrf_token = get_or_create_csrf_token(request)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"request": request, "error": None, "csrf_token": csrf_token}
    )


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    if not is_valid_csrf(request, csrf_token):
        print("[Auth] CSRF validation failed on /login", flush=True)
        new_token = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.", "csrf_token": new_token}
        )

    try:
        wp_data = await login_with_wordpress(username, password)
    except WPAuthError as e:
        csrf_token_new = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": str(e), "csrf_token": csrf_token_new}
        )

    user = get_or_create_user(
        db,
        email=wp_data["email"],
        nicename=wp_data["nicename"],
        display_name=wp_data["display_name"],
    )

    request.session["local_user_id"] = user.id
    request.session["wp_token"] = wp_data["token"]

    return RedirectResponse(url="/", status_code=303)


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse(url="/", status_code=303)


@router.get("/profile")
async def profile_page(request: Request, db: Session = Depends(get_db)):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    csrf_token = get_or_create_csrf_token(request)

    # کد ملی در دیتابیس به‌صورت رمزنگاری‌شده ذخیره است؛
    # فقط در لحظه‌ی نمایش به کاربر خودش رمزگشایی می‌شود.
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

    if not is_valid_csrf(request, csrf_token):
        print("[Auth] CSRF validation failed on /profile", flush=True)
        new_token = get_or_create_csrf_token(request)
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

    user.age = int(age) if age and age.isdigit() else None
    user.gender = gender
    user.national_id = encrypt_value(national_id.strip()) if national_id and national_id.strip() else None
    user.address = address
    user.phone = phone.strip() if phone and phone.strip() else None

    db.commit()
    db.refresh(user)

    new_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "profile.html",
        {
            "request": request,
            "user": user,
            "national_id_display": decrypt_value(user.national_id),
            "saved": True,
            "error": None,
            "csrf_token": new_token,
        }
    )