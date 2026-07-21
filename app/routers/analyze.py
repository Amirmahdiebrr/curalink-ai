import traceback

from fastapi import APIRouter, UploadFile, File, Form, Request, BackgroundTasks, Depends
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.services.report_service import ReportService
from app.services.job_store import create_job, update_job, get_job
from app.services.history_service import save_analysis
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

service = ReportService()


async def run_job(
    job_id: str,
    files: list[tuple[bytes, str]],
    exam_type: str,
    symptoms: str | None,
    patient_age: int | None,
    patient_gender: str | None,
    user_id: int | None,
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
                )
                print(f"[Analyze] Saved analysis to history for user_id={user_id}", flush=True)
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


def _job_belongs_to_user(job: dict, user_id: int | None) -> bool:
    if not user_id:
        return False
    return job.get("user_id") == user_id


@router.post("/analyze")
async def analyze(
    request: Request,
    background_tasks: BackgroundTasks,
    files: list[UploadFile] = File(...),
    exam_type: str = Form(None),
    symptoms: str = Form(None),
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

    user_id = current_user.id
    patient_age = current_user.age
    patient_gender = current_user.gender

    print(f"[Analyze] exam_type received: {exam_type}", flush=True)
    print(f"[Analyze] file count received: {len(files)}", flush=True)
    print(f"[Analyze] symptoms provided: {bool(symptoms and symptoms.strip())}", flush=True)
    print(f"[Analyze] user_id: {user_id}", flush=True)
    print(f"[Analyze] patient_age/gender from profile: {patient_age} / {patient_gender}", flush=True)

    file_data = []
    for uploaded_file in files:
        content = await uploaded_file.read()
        file_data.append((content, uploaded_file.filename))

    job_id = create_job(exam_type, user_id=user_id)

    background_tasks.add_task(
        run_job, job_id, file_data, exam_type, symptoms, patient_age, patient_gender, user_id
    )

    return JSONResponse({"job_id": job_id})


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
        return templates.TemplateResponse(
            request,
            "result.html",
            {"request": request, "result": job["result"], "user": user, "job_id": job_id, "record_id": None, "csrf_token": csrf_token}
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

    return templates.TemplateResponse(
        request,
        "result.html",
        {"request": request, "result": job["result"], "user": user, "job_id": job_id, "record_id": None, "csrf_token": csrf_token}
    )