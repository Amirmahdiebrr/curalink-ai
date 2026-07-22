"""
app/routers/family.py

Add/list/delete family member profiles used when uploading an
analysis on behalf of someone other than the logged-in user.
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.services.family_service import (
    get_family_members,
    create_family_member,
    delete_family_member,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/family")
async def family_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "family.html",
        {
            "request": request,
            "user": user,
            "members": members,
            "csrf_token": csrf_token,
            "error": None,
        }
    )


@router.post("/family")
async def family_add(
    request: Request,
    name: str = Form(...),
    relation: str = Form(None),
    age: str = Form(None),
    gender: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        members = get_family_members(db, user.id)
        new_token = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request,
            "family.html",
            {
                "request": request,
                "user": user,
                "members": members,
                "csrf_token": new_token,
                "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.",
            }
        )

    name = (name or "").strip()

    if not name:
        members = get_family_members(db, user.id)
        new_token = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request,
            "family.html",
            {
                "request": request,
                "user": user,
                "members": members,
                "csrf_token": new_token,
                "error": "نام عضو خانواده نمی‌تواند خالی باشد.",
            }
        )

    age_value = int(age) if age and age.isdigit() else None

    create_family_member(db, user.id, name, relation, age_value, gender or None)

    return RedirectResponse(url="/family", status_code=303)


@router.post("/family/{member_id}/delete")
async def family_delete(
    member_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/family", status_code=303)

    delete_family_member(db, member_id, user.id)

    return RedirectResponse(url="/family", status_code=303)