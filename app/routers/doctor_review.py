"""
app/routers/doctor_review.py

جریان بررسی گزارش توسط پزشک (نظر روی تحلیل AI)، به‌علاوه ابزارهای
تکمیلی: یادداشت‌های پزشکی، نسخه‌ی دیجیتال (با کد پیگیری) و یادآوری
پیگیری بیمار (زمان‌بندی بر اساس نوع بیمه).

کاربران platform_admin هم به این صف دسترسی دارند (برای تست کامل
جریان بررسی پزشک بدون نیاز به اکانت پزشک جداگانه).
"""

from datetime import datetime

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter
from app.models import ROLE_DOCTOR, ROLE_PLATFORM_ADMIN, INSURANCE_TYPES, INSURANCE_LABELS
from app.core.exam_types import EXAM_TYPE_LABELS
from app.services.doctor_review_service import (
    request_review,
    get_awaiting_reviews,
    get_my_reviewed_records,
    get_record_for_doctor,
    submit_review,
    DoctorReviewError,
)
from app.services.family_service import get_family_member_for_user, get_family_members
from app.services.doctor_tools_service import (
    add_doctor_note,
    get_notes_for_analysis,
    delete_doctor_note,
    create_prescription,
    get_prescriptions_for_doctor,
    get_prescriptions_for_analysis,
    get_prescription_for_doctor,
    update_prescription_status,
    create_followup,
    get_followups_for_doctor,
    delete_followup,
    DoctorToolsError,
)
from app.services.pdf_export_service import render_prescription_pdf, PDFExportError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


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
        logger.error(f"[DoctorReview] request_review failed: {e}")

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
    my_prescriptions = get_prescriptions_for_doctor(db, doctor.id)[:5]
    my_followups = get_followups_for_doctor(db, doctor.id)[:5]

    return templates.TemplateResponse(
        request,
        "doctor_reviews.html",
        {
            "request": request,
            "user": doctor,
            "awaiting": awaiting,
            "reviewed": reviewed,
            "exam_type_labels": EXAM_TYPE_LABELS,
            "my_prescriptions": my_prescriptions,
            "my_followups": my_followups,
            "insurance_labels": INSURANCE_LABELS,
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
    notes = get_notes_for_analysis(db, record.id)
    prescriptions = get_prescriptions_for_analysis(db, record.id)

    patient = record.user
    patient_family_members = get_family_members(db, patient.id) if patient else []

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
            "notes": notes,
            "prescriptions": prescriptions,
            "insurance_types": INSURANCE_TYPES,
            "insurance_labels": INSURANCE_LABELS,
            "patient": patient,
            "patient_family_members": patient_family_members,
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
        return RedirectResponse(url=f"/doctor/reviews/{record_id}", status_code=303)

    try:
        submit_review(db, record_id, doctor.id, opinion_text)
    except DoctorReviewError as e:
        logger.error(f"[DoctorReview] submit_review failed: {e}")

    return RedirectResponse(url="/doctor/reviews", status_code=303)


# ==========================
# یادداشت‌های پزشکی
# ==========================

@router.post("/doctor/reviews/{record_id}/notes")
@limiter.limit("60/hour")
async def doctor_note_add(
    record_id: int,
    request: Request,
    note_text: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url=f"/doctor/reviews/{record_id}", status_code=303)

    record = get_record_for_doctor(db, record_id)
    if not record:
        return RedirectResponse(url="/doctor/reviews", status_code=303)

    try:
        add_doctor_note(db, record_id, doctor.id, note_text)
    except DoctorToolsError as e:
        logger.error(f"[DoctorTools] add_doctor_note failed: {e}")

    return RedirectResponse(url=f"/doctor/reviews/{record_id}#doctor-notes", status_code=303)


@router.post("/doctor/notes/{note_id}/delete")
async def doctor_note_delete(
    note_id: int,
    request: Request,
    record_id: int = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url=f"/doctor/reviews/{record_id}", status_code=303)

    delete_doctor_note(db, note_id, doctor.id)

    return RedirectResponse(url=f"/doctor/reviews/{record_id}#doctor-notes", status_code=303)


# ==========================
# نسخه دیجیتال
# ==========================

@router.post("/doctor/reviews/{record_id}/prescriptions")
@limiter.limit("30/hour")
async def doctor_prescription_create(
    record_id: int,
    request: Request,
    db: Session = Depends(get_db),
):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    form = await request.form()

    csrf_token = form.get("csrf_token")
    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url=f"/doctor/reviews/{record_id}", status_code=303)

    record = get_record_for_doctor(db, record_id)
    if not record:
        return RedirectResponse(url="/doctor/reviews", status_code=303)

    patient_family_member_id = None
    fm_raw = (form.get("patient_family_member_id") or "").strip()
    if fm_raw and fm_raw != "self":
        try:
            fm_id = int(fm_raw)
            member = get_family_member_for_user(db, fm_id, record.user_id)
            if member:
                patient_family_member_id = member.id
        except ValueError:
            pass

    drug_names = form.getlist("drug_name[]")
    dosages = form.getlist("dosage[]")
    frequencies = form.getlist("frequency[]")
    durations = form.getlist("duration[]")
    instructions_list = form.getlist("instructions[]")

    items = []
    for i in range(len(drug_names)):
        items.append({
            "drug_name": drug_names[i] if i < len(drug_names) else "",
            "dosage": dosages[i] if i < len(dosages) else "",
            "frequency": frequencies[i] if i < len(frequencies) else "",
            "duration": durations[i] if i < len(durations) else "",
            "instructions": instructions_list[i] if i < len(instructions_list) else "",
        })

    try:
        create_prescription(
            db,
            doctor_id=doctor.id,
            analysis_id=record.id,
            patient_user_id=record.user_id,
            patient_family_member_id=patient_family_member_id,
            patient_display_name=form.get("patient_display_name"),
            insurance_type=form.get("insurance_type"),
            insurance_number=form.get("insurance_number"),
            diagnosis_note=form.get("diagnosis_note"),
            items=items,
        )
    except DoctorToolsError as e:
        logger.error(f"[DoctorTools] create_prescription failed: {e}")

    return RedirectResponse(url=f"/doctor/reviews/{record_id}#doctor-prescriptions", status_code=303)


@router.get("/doctor/prescriptions")
async def doctor_prescriptions_list(request: Request, db: Session = Depends(get_db)):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    prescriptions = get_prescriptions_for_doctor(db, doctor.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "doctor_prescriptions.html",
        {
            "request": request,
            "user": doctor,
            "prescriptions": prescriptions,
            "insurance_labels": INSURANCE_LABELS,
            "csrf_token": csrf_token,
        }
    )


@router.post("/doctor/prescriptions/{prescription_id}/status")
async def doctor_prescription_update_status(
    prescription_id: int,
    request: Request,
    status: str = Form(...),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/doctor/prescriptions", status_code=303)

    try:
        update_prescription_status(db, prescription_id, doctor.id, status)
    except DoctorToolsError as e:
        logger.error(f"[DoctorTools] update_prescription_status failed: {e}")

    return RedirectResponse(url="/doctor/prescriptions", status_code=303)


@router.get("/doctor/prescriptions/{prescription_id}/pdf")
async def doctor_prescription_pdf(prescription_id: int, request: Request, db: Session = Depends(get_db)):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    prescription = get_prescription_for_doctor(db, prescription_id, doctor.id)

    if not prescription:
        return JSONResponse({"error": "این نسخه پیدا نشد یا متعلق به شما نیست."}, status_code=404)

    patient_name = (
        prescription.patient_family_member.name if prescription.patient_family_member
        else (prescription.patient_user.display_name if prescription.patient_user else prescription.patient_display_name)
    ) or "بیمار"

    doctor_specialty = doctor.doctor_profile.specialty if doctor.doctor_profile else None
    doctor_council_no = doctor.doctor_profile.medical_council_no if doctor.doctor_profile else None

    try:
        pdf_bytes = render_prescription_pdf(
            prescription=prescription,
            doctor_name=doctor.display_name,
            doctor_specialty=doctor_specialty,
            doctor_council_no=doctor_council_no,
            patient_name=patient_name,
        )
    except PDFExportError as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="curalink-rx-{prescription.code}.pdf"'}
    )


# ==========================
# یادآوری پیگیری بیمار (مبتنی بر نوع بیمه)
# ==========================

@router.post("/doctor/reviews/{record_id}/followups")
@limiter.limit("30/hour")
async def doctor_followup_create(
    record_id: int,
    request: Request,
    followup_date: str = Form(...),
    note: str = Form(None),
    insurance_type: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url=f"/doctor/reviews/{record_id}", status_code=303)

    record = get_record_for_doctor(db, record_id)
    if not record:
        return RedirectResponse(url="/doctor/reviews", status_code=303)

    try:
        parsed_date = datetime.strptime(followup_date.strip(), "%Y-%m-%d")
    except ValueError:
        return RedirectResponse(url=f"/doctor/reviews/{record_id}#doctor-followups", status_code=303)

    resolved_insurance_type = insurance_type or (record.user.insurance_type if record.user else None)

    try:
        create_followup(
            db,
            doctor_id=doctor.id,
            patient_user_id=record.user_id,
            analysis_id=record.id,
            note=note,
            insurance_type=resolved_insurance_type,
            followup_date=parsed_date,
        )
    except DoctorToolsError as e:
        logger.error(f"[DoctorTools] create_followup failed: {e}")

    return RedirectResponse(url=f"/doctor/reviews/{record_id}#doctor-followups", status_code=303)


@router.get("/doctor/followups")
async def doctor_followups_list(request: Request, db: Session = Depends(get_db)):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    followups = get_followups_for_doctor(db, doctor.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "doctor_followups.html",
        {
            "request": request,
            "user": doctor,
            "followups": followups,
            "insurance_labels": INSURANCE_LABELS,
            "csrf_token": csrf_token,
        }
    )


@router.post("/doctor/followups/{followup_id}/delete")
async def doctor_followup_delete(
    followup_id: int,
    request: Request,
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):
    doctor = _require_approved_doctor(request, db)

    if not doctor:
        return RedirectResponse(url="/login", status_code=303)

    if not is_valid_csrf(request, csrf_token):
        return RedirectResponse(url="/doctor/followups", status_code=303)

    delete_followup(db, followup_id, doctor.id)

    return RedirectResponse(url="/doctor/followups", status_code=303)