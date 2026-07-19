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


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def get_current_user(request: Request, db: Session = Depends(get_db)):
    user_id = request.session.get("local_user_id")
    if not user_id:
        return None
    return db.query(LocalUser).filter(LocalUser.id == user_id).first()


@router.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse(request, "login.html", {"request": request, "error": None})


@router.post("/login")
async def login_submit(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):

    try:
        wp_data = await login_with_wordpress(username, password)
    except WPAuthError as e:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"request": request, "error": str(e)}
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

    return templates.TemplateResponse(request, "profile.html", {"request": request, "user": user, "saved": False})


@router.post("/profile")
async def profile_update(
    request: Request,
    age: str = Form(None),
    gender: str = Form(None),
    national_id: str = Form(None),
    address: str = Form(None),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    user.age = int(age) if age and age.isdigit() else None
    user.gender = gender
    user.national_id = national_id
    user.address = address

    db.commit()
    db.refresh(user)

    return templates.TemplateResponse(request, "profile.html", {"request": request, "user": user, "saved": True})