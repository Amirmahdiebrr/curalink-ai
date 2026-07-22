"""
app/routers/visit_prep.py

Generates a "prepare for your doctor visit" summary for the
logged-in user or one of their family members, based on aggregated
lab test history and an optional reason for the visit. Saves it to
history and lets the user browse past summaries.
"""

import markdown
import bleach

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter
from app.services.family_service import get_family_members, get_family_member_for_user
from app.services.visit_prep_service import VisitPrepService
from app.services.visit_prep_history_service import (
    save_visit_prep,
    get_user_visit_preps,
    get_visit_prep_for_user,
)
from app.services.deepseek import DeepSeekError
from app.services.report_service import ALLOWED_TAGS, ALLOWED_ATTRS


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

visit_prep_service = VisitPrepService()

MAX_REASON_LENGTH = 800


def _to_html(raw_text: str) -> str:
    raw_html = markdown.markdown(raw_text, extensions=["extra", "nl2br", "sane_lists"])
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


@router.get("/visit-prep")
async def visit_prep_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "visit_prep.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "csrf_token": csrf_token,
            "summary_html": None,
            "summary_raw": None,
            "record_id": None,
            "error": None,
            "selected_family_member_id": None,
            "reason_value": "",
        }
    )


@router.post("/visit-prep")
@limiter.limit("15/hour")
async def visit_prep_generate(
    request: Request,
    family_member_id: str = Form("self"),
    reason: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    new_token = get_or_create_csrf_token(request)
    reason_value = (reason or "").strip()[:MAX_REASON_LENGTH]

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "visit_prep.html",
            {
                "request": request,
                "user": user,
                "family_members": family_members,
                "csrf_token": new_token,
                "summary_html": None,
                "summary_raw": None,
                "record_id": None,
                "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.",
                "selected_family_member_id": None,
                "reason_value": reason_value,
            }
        )

    resolved_family_member_id = None
    age = user.age
    gender = user.gender

    if family_member_id and family_member_id.strip() != "self":
        try:
            fm_id = int(family_member_id.strip())
        except ValueError:
            fm_id = None

        if fm_id:
            member = get_family_member_for_user(db, fm_id, user.id)
            if member:
                resolved_family_member_id = member.id
                age = member.age
                gender = member.gender

    try:
        raw_summary = await visit_prep_service.generate(
            db,
            user_id=user.id,
            family_member_id=resolved_family_member_id,
            age=age,
            gender=gender,
            visit_reason=reason_value,
        )
    except DeepSeekError as e:
        return templates.TemplateResponse(
            request,
            "visit_prep.html",
            {
                "request": request,
                "user": user,
                "family_members": family_members,
                "csrf_token": new_token,
                "summary_html": None,
                "summary_raw": None,
                "record_id": None,
                "error": f"اتصال به سرویس هوش مصنوعی برقرار نشد: {e}",
                "selected_family_member_id": resolved_family_member_id,
                "reason_value": reason_value,
            }
        )

    summary_html = _to_html(raw_summary)

    record = save_visit_prep(
        db,
        user_id=user.id,
        family_member_id=resolved_family_member_id,
        visit_reason=reason_value or None,
        summary_text=raw_summary,
        summary_html=summary_html,
    )

    return templates.TemplateResponse(
        request,
        "visit_prep.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "csrf_token": new_token,
            "summary_html": summary_html,
            "summary_raw": raw_summary,
            "record_id": record.id,
            "error": None,
            "selected_family_member_id": resolved_family_member_id,
            "reason_value": reason_value,
        }
    )


@router.get("/visit-prep/history")
async def visit_prep_history_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    records = get_user_visit_preps(db, user.id)

    return templates.TemplateResponse(
        request,
        "visit_prep_history.html",
        {
            "request": request,
            "user": user,
            "records": records,
        }
    )


@router.get("/visit-prep/history/{record_id}")
async def visit_prep_history_detail(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_visit_prep_for_user(db, record_id, user.id)

    if not record:
        return RedirectResponse(url="/visit-prep/history", status_code=303)

    family_members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "visit_prep.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "csrf_token": csrf_token,
            "summary_html": record.summary_html,
            "summary_raw": record.summary_text,
            "record_id": record.id,
            "error": None,
            "selected_family_member_id": record.family_member_id,
            "reason_value": record.visit_reason or "",
        }
    )