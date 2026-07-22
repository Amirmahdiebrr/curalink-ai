"""
app/routers/admin.py

Platform-admin panel: review and approve/reject pending doctor
registrations. Only accessible to users with role=platform_admin.
"""

from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import ROLE_PLATFORM_ADMIN
from app.routers.auth import get_current_user
from app.services.auth_service import (
    get_pending_doctors,
    get_reviewed_doctors,
    approve_doctor,
    reject_doctor,
    AuthError,
)
from app.services.email_service import EmailService
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

email_service = EmailService()


def _require_admin(request: Request, db: Session):
    user = get_current_user(request, db)
    if not user or user.role != ROLE_PLATFORM_ADMIN:
        return None
    return user


@router.get("/admin/doctors")
async def admin_doctors_page(request: Request, db: Session = Depends(get_db)):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    pending = get_pending_doctors(db)
    reviewed = get_reviewed_doctors(db)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "admin_doctors.html",
        {
            "request": request,
            "user": admin_user,
            "pending": pending,
            "reviewed": reviewed,
            "csrf_token": csrf_token,
            "error": None,
        }
    )


@router.post("/admin/doctors/{doctor_id}/approve")
@limiter.limit("30/hour")
async def admin_approve_doctor(
    doctor_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/admin/doctors", status_code=303)

    try:
        doctor = approve_doctor(db, doctor_id, admin_user.id)
        background_tasks.add_task(email_service.send_doctor_approval_notice, doctor.email, True)
    except AuthError as e:
        print(f"[Admin] Approve doctor failed: {e}", flush=True)

    return RedirectResponse(url="/admin/doctors", status_code=303)


@router.post("/admin/doctors/{doctor_id}/reject")
@limiter.limit("30/hour")
async def admin_reject_doctor(
    doctor_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    note: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/admin/doctors", status_code=303)

    try:
        doctor = reject_doctor(db, doctor_id, admin_user.id, note=(note or "").strip() or None)
        background_tasks.add_task(email_service.send_doctor_approval_notice, doctor.email, False)
    except AuthError as e:
        print(f"[Admin] Reject doctor failed: {e}", flush=True)

    return RedirectResponse(url="/admin/doctors", status_code=303)