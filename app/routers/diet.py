"""
app/routers/diet.py
"""

import markdown
import bleach

from fastapi import APIRouter, Request, Form, Depends
from fastapi.templating import Jinja2Templates
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.database import get_db
from app.routers.auth import get_current_user
from app.core.csrf import get_or_create_csrf_token, is_valid_csrf
from app.core.limiter import limiter
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
from app.models import PURPOSE_DIET_PLAN


router = APIRouter()

templates = Jinja2Templates(directory="app/templates")

diet_service = DietService()
chat_service = ChatService()

MAX_CONTEXT_LENGTH = 800


def _to_html(raw_text: str) -> str:
    raw_html = markdown.markdown(raw_text, extensions=["extra", "nl2br", "sane_lists"])
    return bleach.clean(raw_html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRS, strip=True)


async def generate_and_save_diet_plan(
    db: Session,
    user_id: int,
    family_member_id: int | None,
    age: int | None,
    gender: str | None,
    context_value: str | None,
):
    raw_plan = await diet_service.generate(
        db,
        user_id=user_id,
        family_member_id=family_member_id,
        age=age,
        gender=gender,
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
    age = user.age
    gender = user.gender

    if family_member_id and family_member_id.strip() != "self":
        try:
            fm_id = int(family_member_id.strip())
        except ValueError:
            fm_id = None

        if fm_id:
            member = get_family_member_for_user(db, fm_id, user.id)
            if member:
                resolved_family_member_id = member.id
                age = member.age
                gender = member.gender

    access = check_diet_plan_access(db, user.id)

    if not access["free"]:
        try:
            payment_result = await start_service_payment(
                db,
                user,
                PURPOSE_DIET_PLAN,
                access["price"],
                "خرید برنامه غذایی هوشمند",
                {
                    "user_id": user.id,
                    "family_member_id": resolved_family_member_id,
                    "age": age,
                    "gender": gender,
                    "context_value": context_value,
                },
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
                    "error": f"اتصال به درگاه پرداخت برقرار نشد: {e}",
                    "selected_family_member_id": resolved_family_member_id,
                    "context_value": context_value,
                }
            )

        return RedirectResponse(url=payment_result["payment_url"], status_code=303)

    try:
        record = await generate_and_save_diet_plan(
            db,
            user_id=user.id,
            family_member_id=resolved_family_member_id,
            age=age,
            gender=gender,
            context_value=context_value,
        )
    except DeepSeekError as e:
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
                "error": f"اتصال به سرویس هوش مصنوعی برقرار نشد: {e}",
                "selected_family_member_id": resolved_family_member_id,
                "context_value": context_value,
            }
        )

    return templates.TemplateResponse(
        request,
        "diet.html",
        {
            "request": request,
            "user": user,
            "family_members": family_members,
            "csrf_token": new_token,
            "diet_plan_html": record.plan_html,
            "diet_plan_raw": record.plan_text,
            "diet_record_id": record.id,
            "error": None,
            "selected_family_member_id": resolved_family_member_id,
            "context_value": context_value,
        }
    )


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
        print("[DietChat] Rejected: invalid CSRF token", flush=True)
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
            {"error": "اتصال به سرویس هوش مصنوعی برقرار نشد. لطفاً از فعال بودن اتصال (VPN) سرور مطمئن شوید و دوباره تلاش کنید."},
            status_code=503
        )
    except Exception as e:
        print(f"[DietChat] Unexpected error: {e}", flush=True)
        return JSONResponse({"error": "پاسخ‌گویی با خطا مواجه شد. لطفاً دوباره تلاش کنید."}, status_code=500)

    return JSONResponse({"answer": answer})