"""
app/routers/admin.py

Platform-admin panel:
- /admin: داشبورد نظارتی کلی
- /admin/analysis/{id}: مشاهده‌ی هر گزارش آزمایشی از هر کاربری
- /admin/doctors: بررسی و تایید/رد ثبت‌نام پزشکان + مشاهده مدرک
- /admin/users: مدیریت و حذف کاربران، اعطای دسترسی نامحدود رایگان

فقط برای کاربرانی با role=platform_admin در دسترس است.
"""

from pathlib import Path

from fastapi import APIRouter, Request, Form, Depends, BackgroundTasks
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, FileResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import (
    ROLE_PLATFORM_ADMIN, ROLE_PATIENT, ROLE_DOCTOR, ROLE_ORG_ADMIN,
    User, AnalysisRecord, Payment, Subscription,
    PAYMENT_PAID, SUBSCRIPTION_ACTIVE, DOCTOR_REVIEW_AWAITING_DOCTOR,
    VERIFICATION_PENDING,
)
from app.routers.auth import get_current_user
from app.services.auth_service import (
    get_pending_doctors,
    get_reviewed_doctors,
    approve_doctor,
    reject_doctor,
    admin_delete_user,
    AuthError,
)
from app.services.email_service import EmailService
from app.services.history_service import get_record_for_admin, get_test_results_for_analysis
from app.services.organ_display_service import group_results_by_organ
from app.services.billing_service import (
    grant_unlimited_access,
    revoke_unlimited_access,
    BillingError,
)
from app.core.exam_types import EXAM_TYPE_LABELS
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

email_service = EmailService()

DOCTOR_DOCS_DIR = Path("uploads/doctor_docs").resolve()


def _require_admin(request: Request, db: Session):
    user = get_current_user(request, db)
    if not user or user.role != ROLE_PLATFORM_ADMIN:
        return None
    return user


# ==========================
# داشبورد نظارتی کلی
# ==========================

@router.get("/admin")
async def admin_dashboard(request: Request, db: Session = Depends(get_db)):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    stats = {
        "total_patients": db.query(User).filter(User.role == ROLE_PATIENT).count(),
        "total_doctors": db.query(User).filter(User.role == ROLE_DOCTOR).count(),
        "total_orgs": db.query(User).filter(User.role == ROLE_ORG_ADMIN).count(),
        "pending_doctor_approvals": db.query(User).filter(
            User.role == ROLE_DOCTOR, User.verification_status == VERIFICATION_PENDING
        ).count(),
        "total_analyses": db.query(AnalysisRecord).count(),
        "pending_doctor_reviews": db.query(AnalysisRecord).filter(
            AnalysisRecord.review_status == DOCTOR_REVIEW_AWAITING_DOCTOR
        ).count(),
        "active_subscriptions": db.query(Subscription).filter(
            Subscription.status == SUBSCRIPTION_ACTIVE
        ).count(),
        "total_paid_payments": db.query(Payment).filter(Payment.status == PAYMENT_PAID).count(),
    }

    total_revenue_row = (
        db.query(Payment)
        .filter(Payment.status == PAYMENT_PAID)
        .all()
    )
    stats["total_revenue"] = sum(p.amount for p in total_revenue_row)

    recent_analyses = (
        db.query(AnalysisRecord)
        .order_by(AnalysisRecord.created_at.desc())
        .limit(20)
        .all()
    )

    recent_users = (
        db.query(User)
        .order_by(User.created_at.desc())
        .limit(20)
        .all()
    )

    recent_payments = (
        db.query(Payment)
        .order_by(Payment.created_at.desc())
        .limit(20)
        .all()
    )

    return templates.TemplateResponse(
        request,
        "admin_dashboard.html",
        {
            "request": request,
            "user": admin_user,
            "stats": stats,
            "recent_analyses": recent_analyses,
            "recent_users": recent_users,
            "recent_payments": recent_payments,
            "exam_type_labels": EXAM_TYPE_LABELS,
        }
    )


@router.get("/admin/analysis/{record_id}")
async def admin_view_analysis(request: Request, record_id: int, db: Session = Depends(get_db)):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_record_for_admin(db, record_id)

    if not record:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این گزارش پیدا نشد.", "user": admin_user},
            status_code=404,
        )

    test_results = get_test_results_for_analysis(db, record.id)
    organ_groups = group_results_by_organ(test_results)

    result = {
        "exam_type": record.exam_type,
        "filename": record.filename,
        "ocr": record.ocr_text,
        "analysis": record.analysis_text,
        "analysis_html": record.analysis_html,
        "symptoms": record.symptoms,
        "exam_type_mismatch": False,
        "requested_exam_type_label": None,
        "detected_exam_type_label": None,
        "ocr_warning": None,
        "review_status": record.review_status,
        "doctor_opinion_text": record.doctor_opinion_text,
    }

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "request": request,
            "result": result,
            "user": admin_user,
            "job_id": None,
            "record_id": record.id,
            "csrf_token": csrf_token,
            "organ_groups": organ_groups,
        }
    )


# ==========================
# تایید حساب پزشکان
# ==========================

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


@router.get("/admin/doctors/{doctor_id}/document")
async def admin_view_doctor_document(doctor_id: int, request: Request, db: Session = Depends(get_db)):
    """
    نمایش/دانلود امن مدرک نظام پزشکی یک پزشک، فقط برای platform_admin.
    """

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    doctor = db.query(User).filter(User.id == doctor_id, User.role == ROLE_DOCTOR).first()

    if not doctor or not doctor.doctor_profile or not doctor.doctor_profile.license_document_path:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "مدرکی برای این پزشک ثبت نشده است.", "user": admin_user},
            status_code=404,
        )

    file_path = Path(doctor.doctor_profile.license_document_path).resolve()

    if DOCTOR_DOCS_DIR not in file_path.parents and file_path.parent != DOCTOR_DOCS_DIR:
        logger.warning(f"[Admin] Rejected document path outside allowed dir: {file_path}")
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "مسیر فایل نامعتبر است.", "user": admin_user},
            status_code=400,
        )

    if not file_path.exists():
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "فایل مدرک روی سرور پیدا نشد.", "user": admin_user},
            status_code=404,
        )

    return FileResponse(
        path=file_path,
        filename=f"license_{doctor.id}{file_path.suffix}",
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
        logger.error(f"[Admin] Approve doctor failed: {e}")

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
        logger.error(f"[Admin] Reject doctor failed: {e}")

    return RedirectResponse(url="/admin/doctors", status_code=303)


# ==========================
# مدیریت کاربران (حذف توسط ادمین، اعطای دسترسی نامحدود)
# ==========================

@router.get("/admin/users")
async def admin_users_page(request: Request, db: Session = Depends(get_db)):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    users = db.query(User).order_by(User.created_at.desc()).all()
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "admin_users.html",
        {
            "request": request,
            "user": admin_user,
            "users": users,
            "csrf_token": csrf_token,
        }
    )


@router.post("/admin/users/{target_user_id}/delete")
@limiter.limit("20/hour")
async def admin_delete_user_route(
    target_user_id: int,
    request: Request,
    background_tasks: BackgroundTasks,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/admin/users", status_code=303)

    if target_user_id == admin_user.id:
        return RedirectResponse(url="/admin/users", status_code=303)

    try:
        deleted_user = admin_delete_user(db, target_user_id)
        background_tasks.add_task(email_service.send_account_deleted_notice, deleted_user.email, True)
    except AuthError as e:
        logger.error(f"[Admin] Delete user failed: {e}")

    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/admin/users/{target_user_id}/grant-unlimited")
@limiter.limit("30/hour")
async def admin_grant_unlimited_access(
    target_user_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    """
    ادمین پلتفرم می‌تواند به یک کاربر (مثلاً بیمار) دسترسی نامحدود و
    رایگان به همه‌ی سرویس‌های پولی بدهد. این کار معادل رفتار
    platform_admin در billing_service است، اما نقش کاربر تغییر
    نمی‌کند.
    """

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/admin/users", status_code=303)

    try:
        grant_unlimited_access(db, target_user_id, admin_user.id)
    except BillingError as e:
        logger.error(f"[Admin] Grant unlimited access failed: {e}")

    return RedirectResponse(url="/admin/users", status_code=303)


@router.post("/admin/users/{target_user_id}/revoke-unlimited")
@limiter.limit("30/hour")
async def admin_revoke_unlimited_access(
    target_user_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    admin_user = _require_admin(request, db)

    if not admin_user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/admin/users", status_code=303)

    try:
        revoke_unlimited_access(db, target_user_id)
    except BillingError as e:
        logger.error(f"[Admin] Revoke unlimited access failed: {e}")

    return RedirectResponse(url="/admin/users", status_code=303)