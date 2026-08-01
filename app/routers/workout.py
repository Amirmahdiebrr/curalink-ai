"""
app/routers/workout.py
"""

import markdown
import bleach

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse, Response
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.crypto import decrypt_value
from app.core.limiter import limiter
from app.core.health_profile import person_health_fields
from app.services.family_service import get_family_members, get_family_member_for_user
from app.services.workout_service import WorkoutService
from app.services.workout_history_service import (
    save_workout_plan,
    get_user_workout_plans,
    get_workout_plan_for_user,
)
from app.services.chat_service import ChatService
from app.services.deepseek import DeepSeekError
from app.services.report_service import ALLOWED_TAGS, ALLOWED_ATTRS
from app.services.billing_service import check_workout_plan_access
from app.services.payment_service import start_service_payment, PaymentError
from app.services.pdf_export_service import render_generic_pdf, PDFExportError
from app.models import PURPOSE_WORKOUT_PLAN
from app.core.logging_config import get_logger

logger = get_logger(__name__)


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

workout_service = WorkoutService()
chat_service = ChatService()

MAX_INJURIES_LENGTH = 800


def _to_html(raw_text: str) -> str:
    raw_html = markdown.markdown(raw_text, extensions=["extra", "nl2br", "sane_lists"])
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


async def generate_and_save_workout_plan(
    db: Session,
    user_id: int,
    family_member_id: int | None,
    health_profile_fields: dict,
    goal: str | None,
    fitness_level: str | None,
    days_per_week: int | None,
    equipment: str | None,
    injuries_value: str | None,
):
    raw_plan = await workout_service.generate(
        db,
        user_id=user_id,
        family_member_id=family_member_id,
        health_profile_fields=health_profile_fields,
        goal=goal,
        fitness_level=fitness_level,
        days_per_week=days_per_week,
        equipment=equipment,
        injuries=injuries_value,
    )

    plan_html = _to_html(raw_plan)

    record = save_workout_plan(
        db,
        user_id=user_id,
        family_member_id=family_member_id,
        goal=goal,
        fitness_level=fitness_level,
        days_per_week=days_per_week,
        equipment=equipment,
        injuries=injuries_value or None,
        plan_text=raw_plan,
        plan_html=plan_html,
    )

    return record


def _empty_context(user, family_members, csrf_token, error=None, selected_family_member_id=None,
                    goal_value="general_fitness", fitness_level_value="beginner",
                    days_per_week_value=3, equipment_value="none", injuries_value=""):
    return {
        "user": user,
        "family_members": family_members,
        "csrf_token": csrf_token,
        "plan_html": None,
        "plan_raw": None,
        "workout_record_id": None,
        "error": error,
        "selected_family_member_id": selected_family_member_id,
        "goal_value": goal_value,
        "fitness_level_value": fitness_level_value,
        "days_per_week_value": days_per_week_value,
        "equipment_value": equipment_value,
        "injuries_value": injuries_value,
    }


@router.get("/workout")
async def workout_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    context = _empty_context(user, family_members, csrf_token)
    context["request"] = request

    return templates.TemplateResponse(request, "workout.html", context)


@router.post("/workout")
@limiter.limit("15/hour")
async def workout_generate(
    request: Request,
    family_member_id: str = Form("self"),
    goal: str = Form("general_fitness"),
    fitness_level: str = Form("beginner"),
    days_per_week: str = Form("3"),
    equipment: str = Form("none"),
    injuries: str = Form(None),
    csrf_token: str = Form(...),
    db: Session = Depends(get_db),
):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    family_members = get_family_members(db, user.id)
    new_token = get_or_create_csrf_token(request)
    injuries_value = (injuries or "").strip()[:MAX_INJURIES_LENGTH]

    try:
        days_per_week_int = int(days_per_week)
    except (TypeError, ValueError):
        days_per_week_int = 3

    if not is_valid_csrf(request, csrf_token):
        context = _empty_context(
            user, family_members, new_token,
            error="خطای اعتبارسنجی امنیتی. لطفاً دوباره تلاش کنید.",
            goal_value=goal, fitness_level_value=fitness_level,
            days_per_week_value=days_per_week_int, equipment_value=equipment,
            injuries_value=injuries_value,
        )
        context["request"] = request
        return templates.TemplateResponse(request, "workout.html", context)

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

    access = check_workout_plan_access(db, user.id)

    if not access["free"]:
        try:
            payment_result = await start_service_payment(
                db,
                user,
                PURPOSE_WORKOUT_PLAN,
                access["price"],
                "خرید برنامه ورزشی هوشمند",
                {
                    "user_id": user.id,
                    "family_member_id": resolved_family_member_id,
                    "health_profile_fields": health_profile_fields,
                    "goal": goal,
                    "fitness_level": fitness_level,
                    "days_per_week": days_per_week_int,
                    "equipment": equipment,
                    "injuries_value": injuries_value,
                },
            )
        except PaymentError as e:
            context = _empty_context(
                user, family_members, new_token,
                error=f"اتصال به درگاه پرداخت برقرار نشد: {e}",
                selected_family_member_id=resolved_family_member_id,
                goal_value=goal, fitness_level_value=fitness_level,
                days_per_week_value=days_per_week_int, equipment_value=equipment,
                injuries_value=injuries_value,
            )
            context["request"] = request
            return templates.TemplateResponse(request, "workout.html", context)

        return RedirectResponse(url=payment_result["payment_url"], status_code=303)

    try:
        record = await generate_and_save_workout_plan(
            db,
            user_id=user.id,
            family_member_id=resolved_family_member_id,
            health_profile_fields=health_profile_fields,
            goal=goal,
            fitness_level=fitness_level,
            days_per_week=days_per_week_int,
            equipment=equipment,
            injuries_value=injuries_value,
        )
    except DeepSeekError as e:
        context = _empty_context(
            user, family_members, new_token,
            error=f"اتصال به سرویس هوش مصنوعی برقرار نشد: {e}",
            selected_family_member_id=resolved_family_member_id,
            goal_value=goal, fitness_level_value=fitness_level,
            days_per_week_value=days_per_week_int, equipment_value=equipment,
            injuries_value=injuries_value,
        )
        context["request"] = request
        return templates.TemplateResponse(request, "workout.html", context)

    context = {
        "request": request,
        "user": user,
        "family_members": family_members,
        "csrf_token": new_token,
        "plan_html": decrypt_value(record.plan_html),
        "plan_raw": decrypt_value(record.plan_text),
        "workout_record_id": record.id,
        "error": None,
        "selected_family_member_id": resolved_family_member_id,
        "goal_value": goal,
        "fitness_level_value": fitness_level,
        "days_per_week_value": days_per_week_int,
        "equipment_value": equipment,
        "injuries_value": injuries_value,
    }

    return templates.TemplateResponse(request, "workout.html", context)


@router.get("/workout/history")
async def workout_history_page(request: Request, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    records = get_user_workout_plans(db, user.id)

    return templates.TemplateResponse(
        request,
        "workout_history.html",
        {"request": request, "user": user, "records": records}
    )


@router.get("/workout/history/{record_id}")
async def workout_history_detail(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_workout_plan_for_user(db, record_id, user.id)

    if not record:
        return RedirectResponse(url="/workout/history", status_code=303)

    family_members = get_family_members(db, user.id)
    csrf_token = get_or_create_csrf_token(request)

    context = {
        "request": request,
        "user": user,
        "family_members": family_members,
        "csrf_token": csrf_token,
        "plan_html": record.plan_html,
        "plan_raw": record.plan_text,
        "workout_record_id": record.id,
        "error": None,
        "selected_family_member_id": record.family_member_id,
        "goal_value": record.goal or "general_fitness",
        "fitness_level_value": record.fitness_level or "beginner",
        "days_per_week_value": record.days_per_week or 3,
        "equipment_value": record.equipment or "none",
        "injuries_value": record.injuries or "",
    }

    return templates.TemplateResponse(request, "workout.html", context)


@router.get("/workout/pdf/{record_id}")
async def workout_pdf(request: Request, record_id: int, db: Session = Depends(get_db)):

    user = get_current_user(request, db)

    if not user:
        return RedirectResponse(url="/login", status_code=303)

    record = get_workout_plan_for_user(db, record_id, user.id)

    if not record:
        return JSONResponse({"error": "این برنامه ورزشی پیدا نشد یا به شما تعلق ندارد."}, status_code=404)

    patient_name = record.family_member.name if record.family_member else user.display_name

    try:
        pdf_bytes = render_generic_pdf(
            document_title="برنامه ورزشی شخصی‌سازی‌شده",
            section_heading="برنامه تمرینی پیشنهادی",
            patient_name=patient_name,
            report_date=record.created_at,
            content_html=record.plan_html or "",
            extra_meta={"محدودیت/آسیب جسمی وارد‌شده": record.injuries},
            disclaimer_text="این برنامه ورزشی صرفاً یک پیشنهاد کلی است و جایگزین نظر پزشک، فیزیوتراپیست یا مربی حضوری نیست.",
        )
    except PDFExportError as e:
        logger.error(f"[Workout] PDF export failed for record_id={record_id}: {e}")
        return JSONResponse({"error": str(e)}, status_code=500)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="curalink-workout-{record_id}.pdf"'}
    )


class WorkoutChatTurn(BaseModel):
    role: str
    content: str


class WorkoutChatRequest(BaseModel):
    workout_plan_text: str
    question: str
    history: list[WorkoutChatTurn] = []


@router.post("/workout/chat")
@limiter.limit("15/minute")
async def workout_chat(request: Request, payload: WorkoutChatRequest, db: Session = Depends(get_db)):

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

    plan_text = (payload.workout_plan_text or "").strip()

    if not plan_text:
        return JSONResponse({"error": "برنامه ورزشی مرتبط پیدا نشد."}, status_code=400)

    history_data = [turn.model_dump() for turn in payload.history]

    try:
        answer = await chat_service.ask(plan_text, history_data, question)
    except DeepSeekError:
        return JSONResponse(
            {"error": "اتصال به سرویس هوش مصنوعی برقرار نشد. لطفاً دوباره تلاش کنید."},
            status_code=503
        )
    except Exception as e:
        logger.error(f"[WorkoutChat] Unexpected error: {e}")
        return JSONResponse({"error": "پاسخ‌گویی با خطا مواجه شد. لطفاً دوباره تلاش کنید."}, status_code=500)

    return JSONResponse({"answer": answer})