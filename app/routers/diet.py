"""
app/routers/diet.py
"""

import asyncio

import markdown
import bleach

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.crypto import decrypt_value
from app.core.limiter import limiter
from app.core.health_profile import person_health_fields
from app.services.family_service import get_family_members, get_family_member_for_user
from app.services.diet_service import DietService
from app.services.diet_history_service import (
    save_diet_plan,
    get_user_diet_plans,
    get_diet_plan_for_user,
)
from app.services.chat_service import ChatService
from app.services.deepseek import DeepSeekError
from app.services.report_service import ALLOWED_TAGS, ALLOWED_ATTRS
from app.services.billing_service import check_diet_plan_access
from app.services.payment_service import start_service_payment, PaymentError
from app.services.pdf_export_service import render_generic_pdf, PDFExportError
from app.services.generic_job_store import create_job, update_job
from app.models import PURPOSE_DIET_PLAN
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

diet_service = DietService()
chat_service = ChatService()

MAX_CONTEXT_LENGTH = 800

GENERIC_AI_ERROR = "اتصال به سرویس هوش مصنوعی برقرار نشد. لطفاً چند لحظه دیگر دوباره تلاش کنید."


def _to_html(raw_text: str) -> str:
    raw_html = markdown.markdown(raw_text, extensions=["extra", "nl2br", "sane_lists"])
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


async def generate_and_save_diet_plan(
    db: Session,
    user_id: int,
    family_member_id: int | None,
    health_profile_fields: dict,
    context_value: str | None,
):
    raw_plan = await diet_service.generate(
        db,
        user_id=user_id,
        family_member_id=family_member_id,
        health_profile_fields=health_profile_fields,
        extra_context=context_value,
    )

    diet_plan_html = _to_html(raw_plan)

    record = save_diet_plan(
        db,
        user_id=user_id,
        family_member_id=family_member_id,
        context=context_value or None,
        plan_text=raw_plan,
        plan_html=diet_plan_html,
    )

    return record


async def run_diet_job(job_id: str, kwargs: dict):
    """
    اجرای واقعی تولید برنامه غذایی در پس‌زمینه (بعد از پرداخت موفق یا
    مستقیم اگر رایگان بود)، با یک session دیتابیس مستقل از request.
    """
    update_job(job_id, status="processing")

    db = SessionLocal()
    try:
        record = await generate_and_save_diet_plan(db, **kwargs)
        update_job(job_id, status="done", result_type="diet_record", result_id=record.id)
    except DeepSeekError as e:
        logger.error(f"[Diet] Background job failed: {e}")
        update_job(job_id, status="error", error=GENERIC_AI_ERROR)
    except Exception as e:
        logger.error(f"[Diet] Unexpected background job error: {e}")
        update_job(job_id, status="error", error="خطای غیرمنتظره در تولید برنامه غذایی.")
    finally:
        db.close()


async def start_diet_background_job(kwargs: dict, user_id: int | None) -> str:
    job_id = create_job("diet", user_id=user_id)
    asyncio.create_task(run_diet_job(job_id, kwargs))
    return job_id


@router.get("/diet")
async def diet_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "diet.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "csrf_token": csrf_token,
            "diet_plan_html": None,
            "diet_plan_raw": None,
            "diet_record_id": None,
            "error": None,
            "selected_family_member_id": None,
            "context_value": "",
        }
    )


@router.post("/diet")
@limiter.limit("15/hour")
async def diet_generate(
    request: Request,
    family_member_id: str = Form("self"),
    context: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    new_token = get_or_create_csrf_token(request)
    context_value = (context or "").strip()[:MAX_CONTEXT_LENGTH]

    if not is_valid_csrf(request, csrf_token):
        return templates.TemplateResponse(
            request,
            "diet.html",
            {
                "request": request,
                "user": user,
                "family_members": family_members,
                "csrf_token": new_token,
                "diet_plan_html": None,
                "diet_plan_raw": None,
                "diet_record_id": None,
                "error": "خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.",
                "selected_family_member_id": None,
                "context_value": context_value,
            }
        )

    resolved_family_member_id = None
    person = user

    if family_member_id and family_member_id.strip() != "self":
        try:
            fm_id = int(family_member_id.strip())
        except ValueError:
            fm_id = None

        if fm_id:
            member = get_family_member_for_user(db, fm_id, user.id)
            if member:
                resolved_family_member_id = member.id
                person = member

    health_profile_fields = person_health_fields(person)

    access = check_diet_plan_access(db, user.id)

    job_kwargs = {
        "user_id": user.id,
        "family_member_id": resolved_family_member_id,
        "health_profile_fields": health_profile_fields,
        "context_value": context_value,
    }

    if not access["free"]:
        try:
            payment_result = await start_service_payment(
                db,
                user,
                PURPOSE_DIET_PLAN,
                access["price"],
                "خرید برنامه غذایی هوشمند",
                job_kwargs,
            )
        except PaymentError as e:
            return templates.TemplateResponse(
                request,
                "diet.html",
                {
                    "request": request,
                    "user": user,
                    "family_members": family_members,
                    "csrf_token": new_token,
                    "diet_plan_html": None,
                    "diet_plan_raw": None,
                    "diet_record_id": None,
                    "error": str(e),
                    "selected_family_member_id": resolved_family_member_id,
                    "context_value": context_value,
                }
            )

        return RedirectResponse(url=payment_result["payment_url"], status_code=303)

    job_id = await start_diet_background_job(job_kwargs, user.id)

    return RedirectResponse(url=f"/generic-processing/{job_id}", status_code=303)


@router.get("/diet/history")
async def diet_history_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    records = get_user_diet_plans(db, user.id)

    return templates.TemplateResponse(
        request,
        "diet_history.html",
        {
            "request": request,
            "user": user,
            "records": records,
        }
    )


@router.get("/diet/history/{record_id}")
async def diet_history_detail(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_diet_plan_for_user(db, record_id, user.id)

    if not record:
        return RedirectResponse(url="/diet/history", status_code=303)

    family_members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    return templates.TemplateResponse(
        request,
        "diet.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "csrf_token": csrf_token,
            "diet_plan_html": record.plan_html,
            "diet_plan_raw": record.plan_text,
            "diet_record_id": record.id,
            "error": None,
            "selected_family_member_id": record.family_member_id,
            "context_value": record.context or "",
        }
    )


@router.get("/diet/pdf/{record_id}")
async def diet_pdf(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_diet_plan_for_user(db, record_id, user.id)

    if not record:
        return JSONResponse({"error": "این برنامه غذایی پیدا نشد یا به شما تعلق ندارد."}, status_code=404)

    patient_name = record.family_member.name if record.family_member else user.display_name

    try:
        pdf_bytes = await render_generic_pdf(
            document_title="برنامه غذایی شخصی‌سازی‌شده",
            section_heading="برنامه غذایی پیشنهادی",
            patient_name=patient_name,
            report_date=record.created_at,
            content_html=record.plan_html or "",
            extra_meta={"شرح وضعیت خاص وارد‌شده": record.context},
            disclaimer_text="این برنامه غذایی صرفاً یک پیشنهاد کلی بر اساس نتایج آزمایش است و جایگزین ویزیت متخصص تغذیه یا پزشک نیست.",
        )
    except PDFExportError as e:
        logger.error(f"[Diet] PDF export failed for record_id={record_id}: {e}")
        return JSONResponse({"error": "تولید فایل PDF با خطا مواجه شد. لطفاً دوباره تلاش کنید."}, status_code=500)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="curalink-diet-{record_id}.pdf"'}
    )


class DietChatTurn(BaseModel):
    role: str
    content: str


class DietChatRequest(BaseModel):
    diet_plan_text: str
    question: str
    history: list[DietChatTurn] = []


@router.post("/diet/chat")
@limiter.limit("15/minute")
async def diet_chat(request: Request, payload: DietChatRequest, db: Session = Depends(get_db)):

    csrf_header = request.headers.get("X-CSRF-Token")

    if not is_valid_csrf(request, csrf_header):
        return JSONResponse({"error": "خطای اعتبارسنجی امنیتی. لطفاً صفحه را رفرش کنید."}, status_code=403)

    user = get_current_user(request, db)

    if not user:
        return JSONResponse({"error": "برای این بخش باید وارد حساب کاربری شوید."}, status_code=401)

    question = (payload.question or "").strip()

    if not question:
        return JSONResponse({"error": "سوال خالی است."}, status_code=400)

    if len(question) > 1000:
        return JSONResponse({"error": "سوال بیش از حد طولانی است."}, status_code=400)

    diet_plan_text = (payload.diet_plan_text or "").strip()

    if not diet_plan_text:
        return JSONResponse({"error": "برنامه غذایی مرتبط پیدا نشد."}, status_code=400)

    history_data = [turn.model_dump() for turn in payload.history]

    try:
        answer = await chat_service.ask(diet_plan_text, history_data, question)
    except DeepSeekError:
        return JSONResponse(
            {"error": GENERIC_AI_ERROR},
            status_code=503
        )
    except Exception as e:
        logger.error(f"[DietChat] Unexpected error: {e}")
        return JSONResponse({"error": "پاسخ‌گویی با خطا مواجه شد. لطفاً دوباره تلاش کنید."}, status_code=500)

    return JSONResponse({"answer": answer})