"""
app/routers/history.py

Displays a logged-in user's past analyses: a list view (/history),
a detail view (/history/{record_id}), and a PDF export
(/history/{record_id}/pdf) that reuses the same underlying data as
result.html.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse, Response
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token
from app.core.exam_types import EXAM_TYPE_LABELS
from app.services.history_service import (
    get_user_history,
    get_record_for_user,
    get_test_results_for_analysis,
)
from app.services.organ_display_service import group_results_by_organ
from app.services.pdf_export_service import render_analysis_pdf, PDFExportError
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


@router.get("/history")
async def history_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    records = get_user_history(db, user.id)

    return templates.TemplateResponse(
        request,
        "history.html",
        {
            "request": request,
            "user": user,
            "records": records,
            "exam_type_labels": EXAM_TYPE_LABELS,
        }
    )


@router.get("/history/{record_id}")
async def history_detail(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_record_for_user(db, record_id, user.id)

    if not record:
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این گزارش پیدا نشد یا به شما تعلق ندارد.", "user": user},
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
            "user": user,
            "job_id": None,
            "record_id": record.id,
            "csrf_token": csrf_token,
            "organ_groups": organ_groups,
        }
    )


@router.get("/history/{record_id}/pdf")
async def history_pdf(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_record_for_user(db, record_id, user.id)

    if not record:
        return JSONResponse({"error": "این گزارش پیدا نشد یا به شما تعلق ندارد."}, status_code=404)

    test_results = get_test_results_for_analysis(db, record.id)
    organ_groups = group_results_by_organ(test_results)

    patient_name = record.family_member.name if record.family_member else user.display_name

    try:
        pdf_bytes = render_analysis_pdf(
            patient_name=patient_name,
            exam_type_label=EXAM_TYPE_LABELS.get(record.exam_type, record.exam_type or "آزمایش"),
            report_date=record.created_at,
            symptoms=record.symptoms,
            analysis_html=record.analysis_html or "",
            organ_groups=organ_groups,
        )
    except PDFExportError as e:
        logger.error(f"[History] PDF export failed for record_id={record_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="curalink-report-{record_id}.pdf"'}
    )