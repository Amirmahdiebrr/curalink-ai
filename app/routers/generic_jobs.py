"""
app/routers/generic_jobs.py

مسیر مشترک برای صفحه‌ی «در حال پردازش» و polling وضعیت job های
diet/workout/visit-prep که بعد از پرداخت در پس‌زمینه اجرا می‌شوند.
"""

from fastapi import APIRouter, Request, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.services.generic_job_store import get_job


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")


JOB_TYPE_TITLES = {
    "diet": "در حال ساخت برنامه غذایی شما",
    "workout": "در حال ساخت برنامه ورزشی شما",
    "visit_prep": "در حال آماده‌سازی خلاصه‌ی ویزیت شما",
}

JOB_TYPE_REDIRECT = {
    "diet": "/diet/history/{result_id}",
    "workout": "/workout/history/{result_id}",
    "visit_prep": "/visit-prep/history/{result_id}",
}


def _job_belongs_to_user(job: dict, user_id: int | None) -> bool:
    if not user_id:
        return False
    return job.get("user_id") == user_id


@router.get("/generic-processing/{job_id}")
async def generic_processing_page(request: Request, job_id: str, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    job = get_job(job_id)

    if not job or not _job_belongs_to_user(job, user.id if user else None):
        return templates.TemplateResponse(
            request,
            "error.html",
            {"request": request, "message": "این درخواست پیدا نشد یا به شما تعلق ندارد.", "user": user},
            status_code=404,
        )

    if job["status"] == "done" and job["result_id"]:
        redirect_path = JOB_TYPE_REDIRECT.get(job["job_type"], "/").format(result_id=job["result_id"])
        return templates.TemplateResponse(
            request,
            "generic_processing.html",
            {
                "request": request,
                "user": user,
                "job_id": job_id,
                "title": JOB_TYPE_TITLES.get(job["job_type"], "در حال پردازش"),
            }
        )

    return templates.TemplateResponse(
        request,
        "generic_processing.html",
        {
            "request": request,
            "user": user,
            "job_id": job_id,
            "title": JOB_TYPE_TITLES.get(job["job_type"], "در حال پردازش"),
        }
    )


@router.get("/job-status/{job_id}")
async def generic_job_status(job_id: str, request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)
    job = get_job(job_id)

    if not job:
        return JSONResponse({"status": "not_found"}, status_code=404)

    if not _job_belongs_to_user(job, user.id if user else None):
        return JSONResponse({"status": "not_found"}, status_code=404)

    response = {"status": job["status"], "error": job["error"]}

    if job["status"] == "done" and job["result_id"]:
        redirect_path = JOB_TYPE_REDIRECT.get(job["job_type"], "/").format(result_id=job["result_id"])
        response["redirect_url"] = redirect_path

    return JSONResponse(response)