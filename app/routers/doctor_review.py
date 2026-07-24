"""
app/routers/doctor_review.py

جریان بررسی گزارش توسط پزشک: صف گزارش‌های در انتظار، ثبت نظر پزشک،
و اکشن «درخواست بررسی» که از صفحه‌ی تاریخچه‌ی بیمار صدا زده می‌شود.

توجه: پرداخت این سرویس هنوز به درگاه واقعی وصل نشده (پروتوتایپ).

کاربران platform_admin هم به این صف دسترسی دارند (برای تست کامل
جریان بررسی پزشک بدون نیاز به اکانت پزشک جداگانه).
"""

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter
from app.models import ROLE_DOCTOR, ROLE_PLATFORM_ADMIN
from app.core.exam_types import EXAM_TYPE_LABELS
from app.services.doctor_review_service import (
    request_review,
    get_awaiting_reviews,
    get_my_reviewed_records,
    get_record_for_doctor,
    submit_review,
    DoctorReviewError,
)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


def _require_approved_doctor(request: Request, db: Session):
    user = get_current_user(request, db)

    if not user:
        return None

    # ادمین پلتفرم همیشه دسترسی کامل دارد (برای تست/نظارت)
    if user.role == ROLE_PLATFORM_ADMIN:
        return user

    if user.role != ROLE_DOCTOR or not user.is_active:
        return None

    return user


# ==========================
# بیمار: درخواست بررسی برای یک گزارش ذخیره‌شده
# ==========================

@router.post("/history/{record_id}/request-review")
@limiter.limit("10/hour")
async def request_review_submit(
    record_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url=f"/history/{record_id}", status_code=303)

    try:
        request_review(db, record_id, user.id)
    except DoctorReviewError as e:
        print(f"[DoctorReview] request_review failed: {e}", flush=True)

    return RedirectResponse(url=f"/history/{record_id}", status_code=303)


# ==========================
# پزشک: صف گزارش‌های در انتظار بررسی
# ==========================

@router.get("/doctor/reviews")
async def doctor_reviews_queue(request: Request, db: Session = Depends(get_db)):

    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    awaiting = get_awaiting_reviews(db)
    reviewed = get_my_reviewed_records(db, doctor.id)

    return templates.TemplateResponse(
        request,
        "doctor_reviews.html",
        {
            "request": request,
            "user": doctor,
            "awaiting": awaiting,
            "reviewed": reviewed,
            "exam_type_labels": EXAM_TYPE_LABELS,
        }
    )


@router.get("/doctor/reviews/{record_id}")
async def doctor_review_detail(request: Request, record_id: int, db: Session = Depends(get_db)):

    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    record = get_record_for_doctor(db, record_id)

    if not record:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این گزارش پیدا نشد یا دیگر قابل بررسی نیست.", "user": doctor},
            status_code=404,
        )

    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "doctor_review_detail.html",
        {
            "request": request,
            "user": doctor,
            "record": record,
            "exam_type_labels": EXAM_TYPE_LABELS,
            "csrf_token": csrf_token,
            "error": None,
        }
    )


@router.post("/doctor/reviews/{record_id}/submit")
@limiter.limit("30/hour")
async def doctor_review_submit(
    record_id: int,
    request: Request,
    opinion_text: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        record = get_record_for_doctor(db, record_id)
        new_token = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request,
            "doctor_review_detail.html",
            {
                "request": request,
                "user": doctor,
                "record": record,
                "exam_type_labels": EXAM_TYPE_LABELS,
                "csrf_token": new_token,
                "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.",
            }
        )

    try:
        submit_review(db, record_id, doctor.id, opinion_text)
    except DoctorReviewError as e:
        record = get_record_for_doctor(db, record_id)
        new_token = get_or_create_csrf_token(request)
        return templates.TemplateResponse(
            request,
            "doctor_review_detail.html",
            {
                "request": request,
                "user": doctor,
                "record": record,
                "exam_type_labels": EXAM_TYPE_LABELS,
                "csrf_token": new_token,
                "error": str(e),
            }
        )

    return RedirectResponse(url="/doctor/reviews", status_code=303)