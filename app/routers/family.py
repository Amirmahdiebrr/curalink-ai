"""
app/routers/family.py
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.health_profile import BLOOD_TYPE_OPTIONS
from app.services.family_service import (
    get_family_members,
    create_family_member,
    delete_family_member,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _parse_int(value: str | None):
    if value and value.strip().isdigit():
        return int(value.strip())
    return None


def _parse_float(value: str | None):
    if value and value.strip():
        try:
            return float(value.strip())
        except ValueError:
            return None
    return None


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
            "blood_type_options": BLOOD_TYPE_OPTIONS,
        }
    )


@router.post("/family")
async def family_add(
    request: Request,
    name: str = Form(...),
    relation: str = Form(None),
    age: str = Form(None),
    gender: str = Form(None),
    height_cm: str = Form(None),
    weight_kg: str = Form(None),
    blood_type: str = Form(None),
    chronic_diseases: str = Form(None),
    allergies: str = Form(None),
    current_medications: str = Form(None),
    surgeries_history: str = Form(None),
    smoking_status: str = Form(None),
    activity_level: str = Form(None),
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
                "blood_type_options": BLOOD_TYPE_OPTIONS,
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
                "blood_type_options": BLOOD_TYPE_OPTIONS,
            }
        )

    age_value = _parse_int(age)
    if age_value is not None and not (0 <= age_value <= 120):
        age_value = None

    create_family_member(
        db,
        user.id,
        name,
        relation,
        age_value,
        gender or None,
        height_cm=_parse_int(height_cm),
        weight_kg=_parse_float(weight_kg),
        blood_type=blood_type or None,
        chronic_diseases=(chronic_diseases or "").strip()[:800] or None,
        allergies=(allergies or "").strip()[:500] or None,
        current_medications=(current_medications or "").strip()[:500] or None,
        surgeries_history=(surgeries_history or "").strip()[:500] or None,
        smoking_status=smoking_status or None,
        activity_level=activity_level or None,
    )

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