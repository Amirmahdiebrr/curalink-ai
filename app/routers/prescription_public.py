"""
app/routers/prescription_public.py

استعلام عمومی نسخه‌ی دیجیتال با کد پیگیری (برای داروخانه‌ها/بیماران)،
بدون نیاز به ورود به حساب کاربری. هیچ اطلاعات حساس اضافی (مثل کد ملی
یا شماره تلفن) نمایش داده نمی‌شود.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.models import INSURANCE_LABELS
from app.services.doctor_tools_service import get_prescription_by_code


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/prescription/verify")
async def prescription_verify_page(request: Request, code: str = None, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    prescription = None
    searched = False

    if code:
        searched = True
        prescription = get_prescription_by_code(db, code)

    patient_name = None
    doctor_name = None

    if prescription:
        patient_name = (
            prescription.patient_family_member.name if prescription.patient_family_member
            else (prescription.patient_user.display_name if prescription.patient_user else prescription.patient_display_name)
        ) or "—"
        doctor_name = prescription.doctor.display_name if prescription.doctor else "—"

    return templates.TemplateResponse(
        request,
        "prescription_verify.html",
        {
            "request": request,
            "user": user,
            "code": code or "",
            "prescription": prescription,
            "searched": searched,
            "patient_name": patient_name,
            "doctor_name": doctor_name,
            "insurance_labels": INSURANCE_LABELS,
        }
    )