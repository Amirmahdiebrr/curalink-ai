"""
app/routers/analyze.py
"""

import asyncio
import base64
import traceback

from fastapi import APIRouter, UploadFile, File, Form, Request, Depends
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.report_service import ReportService
from app.services.job_store import create_job, update_job, get_job
from app.services.history_service import save_analysis
from app.services.family_service import get_family_member_for_user
from app.services.organ_display_service import group_results_by_organ
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter
from app.core.constants import MAX_FILES_PER_REQUEST, MAX_TOTAL_UPLOAD_SIZE_MB
from app.core.exam_types import EXAM_TYPE_LABELS, VALID_EXAM_TYPES
from app.models import PURPOSE_EXAM_ANALYSIS
from app.services.billing_service import check_exam_access, increment_organization_usage, BillingError
from app.services.payment_service import start_service_payment, PaymentError


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

service = ReportService()


def _encode_file_data(file_data: list[tuple[bytes, str]]) -> list[list[str]]:
    """
    بایت خام فایل‌ها را به base64 تبدیل می‌کند تا payload به‌صورت
    JSON-safe باشد؛ چه برای job در حال اجرا، چه برای صف انتظار
    پرداخت که در دیتابیس پرسیست می‌شود.
    """
    return [[base64.b64encode(content).decode("ascii"), filename] for content, filename in file_data]


def _decode_file_data(encoded_file_data: list) -> list[tuple[bytes, str]]:
    return [(base64.b64decode(item[0]), item[1]) for item in encoded_file_data]


async def run_job(
    job_id: str,
    files: list[tuple[bytes, str]],
    exam_type: str,
    symptoms: str | None,
    patient_age: int | None,
    patient_gender: str | None,
    user_id: int | None,
    family_member_id: int | None,
):

    def on_stage(stage: str):
        update_job(job_id, stage=stage)

    update_job(job_id, status="processing", stage="saving")

    try:
        result = await service.process(
            files,
            exam_type=exam_type,
            symptoms=symptoms,
            patient_age=patient_age,
            patient_gender=patient_gender,
            on_stage=on_stage,
        )
        update_job(job_id, status="done", stage="done", result=result)

        if user_id:
            db = SessionLocal()
            try:
                save_analysis(
                    db,
                    user_id=user_id,
                    exam_type=result.get("exam_type", exam_type),
                    filename=result.get("filename"),
                    ocr_text=result.get("ocr", ""),
                    analysis_text=result.get("analysis", ""),
                    analysis_html=result.get("analysis_html", ""),
                    structured_results=result.get("structured_results", []),
                    symptoms=symptoms,
                    family_member_id=family_member_id,
                )
                print(f"[Analyze] Saved analysis to history for user_id={user_id}, family_member_id={family_member_id}", flush=True)
            except Exception as e:
                print(f"[Analyze] Failed to save history: {e}", flush=True)
            finally:
                db.close()

    except Exception as e:
        print("=" * 50)
        print("BACKGROUND JOB ERROR")
        print("=" * 50)
        traceback.print_exc()
        update_job(job_id, status="error", stage="error", error=str(e))


async def start_background_job(payload: dict) -> str:
    """
    یک job جدید می‌سازد و پردازش را به‌صورت asyncio task شروع می‌کند.
    هم از روت /analyze (مسیر رایگان) و هم از payment_service (بعد از
    پرداخت موفق pay-per-use) صدا زده می‌شود.

    payload["file_data"] همیشه لیستی از [base64_string, filename] است
    (نه بایت خام)، چون ممکن است این payload از pending_action_store
    (که در دیتابیس ذخیره می‌شود) بازخوانی شده باشد.
    """
    job_id = create_job(payload.get("exam_type"), user_id=payload.get("user_id"))

    decoded_file_data = _decode_file_data(payload["file_data"])

    asyncio.create_task(run_job(
        job_id,
        decoded_file_data,
        payload.get("exam_type"),
        payload.get("symptoms"),
        payload.get("patient_age"),
        payload.get("patient_gender"),
        payload.get("user_id"),
        payload.get("family_member_id"),
    ))

    return job_id


def _job_belongs_to_user(job: dict, user_id: int | None) -> bool:
    if not user_id:
        return False
    return job.get("user_id") == user_id


@router.post("/analyze")
@limiter.limit("10/hour")
async def analyze(
    request: Request,
    files: list[UploadFile] = File(...),
    exam_type: str = Form(None),
    symptoms: str = Form(None),
    family_member_id: str = Form(None),
    csrf_token: str = Form(None),
    db: Session = Depends(get_db),
):

    current_user = get_current_user(request, db)

    if not current_user:
        print("[Analyze] Rejected: unauthenticated request", flush=True)
        return JSONResponse(
            {"error": "برای استفاده از تحلیل، ابتدا باید وارد حساب کاربری خود شوید.", "login_required": True},
            status_code=401,
        )

    if not is_valid_csrf(request, csrf_token):
        print("[Analyze] Rejected: invalid CSRF token", flush=True)
        return JSONResponse(
            {"error": "خطای اعتبارسنجی امنیتی. لطفاً صفحه را رفرش کرده و دوباره تلاش کنید."},
            status_code=403,
        )

    if len(files) > MAX_FILES_PER_REQUEST:
        return JSONResponse(
            {"error": f"حداکثر {MAX_FILES_PER_REQUEST} فایل در هر درخواست مجاز است."},
            status_code=400,
        )

    user_id = current_user.id
    patient_age = current_user.age
    patient_gender = current_user.gender

    resolved_family_member_id = None

    if family_member_id and family_member_id.strip() and family_member_id.strip() != "self":
        try:
            fm_id = int(family_member_id.strip())
        except ValueError:
            fm_id = None

        if fm_id:
            member = get_family_member_for_user(db, fm_id, user_id)
            if member:
                resolved_family_member_id = member.id
                patient_age = member.age
                patient_gender = member.gender
            else:
                print(f"[Analyze] family_member_id={fm_id} not found for user_id={user_id}, ignoring", flush=True)

    print(f"[Analyze] exam_type received: {exam_type}", flush=True)
    print(f"[Analyze] file count received: {len(files)}", flush=True)
    print(f"[Analyze] symptoms provided: {bool(symptoms and symptoms.strip())}", flush=True)
    print(f"[Analyze] user_id: {user_id}", flush=True)
    print(f"[Analyze] family_member_id resolved: {resolved_family_member_id}", flush=True)
    print(f"[Analyze] patient_age/gender used: {patient_age} / {patient_gender}", flush=True)

    file_data = []
    total_size_mb = 0.0

    for uploaded_file in files:
        content = await uploaded_file.read()
        total_size_mb += len(content) / (1024 * 1024)

        if total_size_mb > MAX_TOTAL_UPLOAD_SIZE_MB:
            return JSONResponse(
                {"error": f"حجم کل فایل‌های ارسالی نباید بیشتر از {MAX_TOTAL_UPLOAD_SIZE_MB} مگابایت باشد."},
                status_code=400,
            )

        file_data.append((content, uploaded_file.filename))

    encoded_file_data = _encode_file_data(file_data)

    pricing_exam_type = exam_type if exam_type in VALID_EXAM_TYPES else "other"

    try:
        access = check_exam_access(db, user_id, pricing_exam_type)
    except BillingError as e:
        return JSONResponse({"error": str(e)}, status_code=500)

    payload = {
        "file_data": encoded_file_data,
        "exam_type": exam_type,
        "symptoms": symptoms,
        "patient_age": patient_age,
        "patient_gender": patient_gender,
        "user_id": user_id,
        "family_member_id": resolved_family_member_id,
    }

    if access["free"]:
        if access.get("org_covered") and access.get("org_user_id"):
            increment_organization_usage(db, access["org_user_id"])

        job_id = await start_background_job(payload)

        return JSONResponse({"job_id": job_id})

    try:
        payment_result = await start_service_payment(
            db,
            current_user,
            PURPOSE_EXAM_ANALYSIS,
            access["price"],
            f"تحلیل آزمایش ({EXAM_TYPE_LABELS.get(pricing_exam_type, pricing_exam_type)})",
            payload,
        )
    except PaymentError as e:
        return JSONResponse({"error": f"اتصال به درگاه پرداخت برقرار نشد: {e}"}, status_code=400)

    return JSONResponse({"payment_required": True, "payment_url": payment_result["payment_url"]})


@router.get("/status/{job_id}")
async def job_status(job_id: str, request: Request, db: Session = Depends(get_db)):

    current_user = get_current_user(request, db)

    job = get_job(job_id)

    if not job:
        return JSONResponse({"status": "not_found"}, status_code=404)

    if not _job_belongs_to_user(job, current_user.id if current_user else None):
        print(f"[Analyze] Unauthorized status access attempt on job_id={job_id}", flush=True)
        return JSONResponse({"status": "not_found"}, status_code=404)

    return JSONResponse({
        "status": job["status"],
        "stage": job["stage"],
        "error": job["error"],
    })


@router.get("/processing/{job_id}")
async def processing_page(request: Request, job_id: str, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    job = get_job(job_id)

    if not job or not _job_belongs_to_user(job, user.id if user else None):
        print(f"[Analyze] Unauthorized processing-page access attempt on job_id={job_id}", flush=True)
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این درخواست پیدا نشد یا به شما تعلق ندارد.", "user": user},
            status_code=404,
        )

    if job["status"] == "done":
        csrf_token = get_or_create_csrf_token(request)
        organ_groups = group_results_by_organ(job["result"].get("structured_results", []))
        return templates.TemplateResponse(
            request,
            "result.html",
            {
                "request": request,
                "result": job["result"],
                "user": user,
                "job_id": job_id,
                "record_id": None,
                "csrf_token": csrf_token,
                "organ_groups": organ_groups,
            }
        )

    return templates.TemplateResponse(
        request,
        "processing.html",
        {"request": request, "job_id": job_id, "not_found": False, "user": user}
    )


@router.get("/result/{job_id}")
async def result_page(request: Request, job_id: str, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    job = get_job(job_id)

    if not job or not _job_belongs_to_user(job, user.id if user else None):
        print(f"[Analyze] Unauthorized result-page access attempt on job_id={job_id}", flush=True)
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این درخواست پیدا نشد یا به شما تعلق ندارد.", "user": user},
            status_code=404,
        )

    if job["status"] != "done":
        return templates.TemplateResponse(
            request,
            "processing.html",
            {"request": request, "job_id": job_id, "not_found": False, "user": user}
        )

    csrf_token = get_or_create_csrf_token(request)
    organ_groups = group_results_by_organ(job["result"].get("structured_results", []))

    return templates.TemplateResponse(
        request,
        "result.html",
        {
            "request": request,
            "result": job["result"],
            "user": user,
            "job_id": job_id,
            "record_id": None,
            "csrf_token": csrf_token,
            "organ_groups": organ_groups,
        }
    )