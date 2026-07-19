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


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

service = ReportService()


async def run_job(job_id: str, content: bytes, filename: str, exam_type: str, user_id: int | None):

    def on_stage(stage: str):
        update_job(job_id, stage=stage)

    update_job(job_id, status="processing", stage="saving")

    try:
        result = await service.process(content, filename, on_stage=on_stage)
        result["exam_type"] = exam_type
        update_job(job_id, status="done", stage="done", result=result)

        if user_id:
            db = SessionLocal()
            try:
                save_analysis(
                    db,
                    user_id=user_id,
                    exam_type=exam_type,
                    filename=result.get("filename"),
                    ocr_text=result.get("ocr", ""),
                    analysis_text=result.get("analysis", ""),
                    analysis_html=result.get("analysis_html", ""),
                    structured_results=result.get("structured_results", []),
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


@router.post("/analyze")
async def analyze(
    request: Request,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    exam_type: str = Form(None),
    db: Session = Depends(get_db),
):

    print(f"[Analyze] exam_type received: {exam_type}", flush=True)

    current_user = get_current_user(request, db)
    user_id = current_user.id if current_user else None

    content = await file.read()
    filename = file.filename

    job_id = create_job(exam_type, user_id=user_id)

    background_tasks.add_task(run_job, job_id, content, filename, exam_type, user_id)

    return JSONResponse({"job_id": job_id})


@router.get("/status/{job_id}")
async def job_status(job_id: str):

    job = get_job(job_id)

    if not job:
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

    if job and job["status"] == "done":
        return templates.TemplateResponse(
            request,
            "result.html",
            {"request": request, "result": job["result"], "user": user}
        )

    return templates.TemplateResponse(
        request,
        "processing.html",
        {"request": request, "job_id": job_id, "not_found": job is None, "user": user}
    )


@router.get("/result/{job_id}")
async def result_page(request: Request, job_id: str, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    job = get_job(job_id)

    if not job or job["status"] != "done":
        return templates.TemplateResponse(
            request,
            "processing.html",
            {"request": request, "job_id": job_id, "not_found": job is None, "user": user}
        )

    return templates.TemplateResponse(
        request,
        "result.html",
        {"request": request, "result": job["result"], "user": user}
    )