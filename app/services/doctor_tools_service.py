"""
app/services/doctor_tools_service.py

سرویس ابزارهای تکمیلی پزشک: یادداشت‌های پزشکی، نسخه‌ی دیجیتال با کد
پیگیری، و یادآوری پیگیری بیمار (زمان‌بندی بر اساس نوع بیمه بیمار).
"""

import secrets
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import (
    DoctorNote, Prescription, PrescriptionItem, PatientFollowup,
    INSURANCE_LABELS,
    PRESCRIPTION_STATUS_ACTIVE, PRESCRIPTION_STATUS_CANCELLED, PRESCRIPTION_STATUS_FULFILLED,
)


class DoctorToolsError(Exception):
    pass


# ==========================
# یادداشت‌های پزشکی
# ==========================

MAX_NOTE_LENGTH = 3000


def add_doctor_note(db: Session, analysis_id: int, doctor_id: int, note_text: str) -> DoctorNote:
    note_text = (note_text or "").strip()

    if not note_text:
        raise DoctorToolsError("متن یادداشت نمی‌تواند خالی باشد.")

    note = DoctorNote(
        analysis_id=analysis_id,
        doctor_id=doctor_id,
        note_text=note_text[:MAX_NOTE_LENGTH],
    )
    db.add(note)
    db.commit()
    db.refresh(note)

    return note


def get_notes_for_analysis(db: Session, analysis_id: int):
    return (
        db.query(DoctorNote)
        .filter(DoctorNote.analysis_id == analysis_id)
        .order_by(DoctorNote.created_at.desc())
        .all()
    )


def delete_doctor_note(db: Session, note_id: int, doctor_id: int) -> bool:
    note = (
        db.query(DoctorNote)
        .filter(DoctorNote.id == note_id, DoctorNote.doctor_id == doctor_id)
        .first()
    )

    if not note:
        return False

    db.delete(note)
    db.commit()
    return True


# ==========================
# نسخه دیجیتال
# ==========================

MAX_PRESCRIPTION_ITEMS = 20


def _generate_prescription_code(db: Session) -> str:
    for _ in range(10):
        code = "RX-" + secrets.token_hex(4).upper()
        exists = db.query(Prescription).filter(Prescription.code == code).first()
        if not exists:
            return code

    raise DoctorToolsError("تولید کد نسخه ناموفق بود. لطفاً دوباره تلاش کنید.")


def create_prescription(
    db: Session,
    doctor_id: int,
    analysis_id: int | None,
    patient_user_id: int | None,
    patient_family_member_id: int | None,
    patient_display_name: str | None,
    insurance_type: str | None,
    insurance_number: str | None,
    diagnosis_note: str | None,
    items: list[dict],
) -> Prescription:

    clean_items = []

    for item in items[:MAX_PRESCRIPTION_ITEMS]:
        drug_name = (item.get("drug_name") or "").strip()
        if not drug_name:
            continue

        clean_items.append({
            "drug_name": drug_name[:200],
            "dosage": (item.get("dosage") or "").strip()[:100] or None,
            "frequency": (item.get("frequency") or "").strip()[:100] or None,
            "duration": (item.get("duration") or "").strip()[:100] or None,
            "instructions": (item.get("instructions") or "").strip()[:300] or None,
        })

    if not clean_items:
        raise DoctorToolsError("حداقل یک داروی معتبر (با نام) باید در نسخه ثبت شود.")

    code = _generate_prescription_code(db)

    prescription = Prescription(
        code=code,
        analysis_id=analysis_id,
        doctor_id=doctor_id,
        patient_user_id=patient_user_id,
        patient_family_member_id=patient_family_member_id,
        patient_display_name=(patient_display_name or "").strip()[:150] or None,
        insurance_type=insurance_type or None,
        insurance_number=(insurance_number or "").strip()[:100] or None,
        diagnosis_note=(diagnosis_note or "").strip()[:1000] or None,
        status=PRESCRIPTION_STATUS_ACTIVE,
    )
    db.add(prescription)
    db.commit()
    db.refresh(prescription)

    for item in clean_items:
        db.add(PrescriptionItem(prescription_id=prescription.id, **item))

    db.commit()
    db.refresh(prescription)

    return prescription


def get_prescription_by_code(db: Session, code: str) -> Prescription | None:
    code = (code or "").strip().upper()

    if not code:
        return None

    return db.query(Prescription).filter(Prescription.code == code).first()


def get_prescriptions_for_doctor(db: Session, doctor_id: int):
    return (
        db.query(Prescription)
        .filter(Prescription.doctor_id == doctor_id)
        .order_by(Prescription.created_at.desc())
        .all()
    )


def get_prescriptions_for_analysis(db: Session, analysis_id: int):
    return (
        db.query(Prescription)
        .filter(Prescription.analysis_id == analysis_id)
        .order_by(Prescription.created_at.desc())
        .all()
    )


def get_prescription_for_doctor(db: Session, prescription_id: int, doctor_id: int) -> Prescription | None:
    return (
        db.query(Prescription)
        .filter(Prescription.id == prescription_id, Prescription.doctor_id == doctor_id)
        .first()
    )


def update_prescription_status(db: Session, prescription_id: int, doctor_id: int, status: str) -> Prescription:
    prescription = get_prescription_for_doctor(db, prescription_id, doctor_id)

    if not prescription:
        raise DoctorToolsError("نسخه پیدا نشد یا متعلق به شما نیست.")

    if status not in (PRESCRIPTION_STATUS_ACTIVE, PRESCRIPTION_STATUS_CANCELLED, PRESCRIPTION_STATUS_FULFILLED):
        raise DoctorToolsError("وضعیت نامعتبر است.")

    prescription.status = status
    db.commit()
    db.refresh(prescription)

    return prescription


# ==========================
# یادآوری پیگیری بیمار (مبتنی بر نوع بیمه)
#
# هر نوع بیمه، سرعت رسیدگی/نوبت‌دهی متفاوتی دارد؛ به همین دلیل تعداد
# روزهای پیش از موعد پیگیری که پیامک یادآوری ارسال می‌شود، بر اساس
# نوع بیمه‌ی بیمار تنظیم می‌شود (بیمه‌های دولتی با نوبت‌دهی کندتر،
# یادآوری زودتر دریافت می‌کنند).
# ==========================

INSURANCE_REMINDER_LEAD_DAYS = {
    "none": 1,
    "tamin_ejtemaei": 3,
    "salamat": 3,
    "niroohaye_mosallah": 5,
    "azad": 1,
    "other": 2,
}


def create_followup(
    db: Session,
    doctor_id: int,
    patient_user_id: int | None,
    analysis_id: int | None,
    note: str | None,
    insurance_type: str | None,
    followup_date: datetime,
) -> PatientFollowup:

    followup = PatientFollowup(
        doctor_id=doctor_id,
        patient_user_id=patient_user_id,
        analysis_id=analysis_id,
        note=(note or "").strip()[:500] or None,
        insurance_type=insurance_type or None,
        followup_date=followup_date,
        reminder_sent=False,
    )
    db.add(followup)
    db.commit()
    db.refresh(followup)

    return followup


def get_followups_for_doctor(db: Session, doctor_id: int):
    return (
        db.query(PatientFollowup)
        .filter(PatientFollowup.doctor_id == doctor_id)
        .order_by(PatientFollowup.followup_date.asc())
        .all()
    )


def delete_followup(db: Session, followup_id: int, doctor_id: int) -> bool:
    followup = (
        db.query(PatientFollowup)
        .filter(PatientFollowup.id == followup_id, PatientFollowup.doctor_id == doctor_id)
        .first()
    )

    if not followup:
        return False

    db.delete(followup)
    db.commit()
    return True


def get_due_patient_followups(db: Session):
    """
    یادآوری‌هایی که با توجه به سرعت نوبت‌دهی نوع بیمه‌ی بیمار، موعد
    ارسال پیامک یادآوری‌شان فرا رسیده و هنوز ارسال نشده‌اند.
    """
    now = datetime.utcnow()

    pending = (
        db.query(PatientFollowup)
        .filter(PatientFollowup.reminder_sent.is_(False))
        .all()
    )

    due = []

    for item in pending:
        lead_days = INSURANCE_REMINDER_LEAD_DAYS.get(item.insurance_type, 1)
        remind_from = item.followup_date - timedelta(days=lead_days)

        if now >= remind_from:
            due.append(item)

    return due